import os
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta

from bokeh.models import Legend
from bokeh.plotting import figure
from bokeh.io import curdoc, export_png
from bokeh.layouts import row, widgetbox
from bokeh.models.widgets import TextInput, DatePicker, Button, DataTable, TableColumn, Div
from bokeh.models import ColumnDataSource, HoverTool, CrosshairTool, BoxZoomTool, ZoomOutTool
from bokeh.models import DatetimeTickFormatter, Tool, String, CustomJS, DateFormatter, NumberFormatter


JS_CODE_SAVE = """import * as p from "core/properties"
import {ActionTool, ActionToolView} from "models/tools/actions/action_tool"
export class NewSaveView extends ActionToolView

  # this is executed when the button is clicked
  doit: () ->
    @plot_view.save(@model.save_name)

export class CustomSaveTool extends ActionTool
  default_view: NewSaveView
  type: "CustomSaveTool"

  tool_name: "Save"
  icon: "bk-tool-icon-save"

  @define { save_name: [ p.String ] } """

class CustomSaveTool(Tool):
    """
    Save a plot with a custom name.
    Usage: CustomSaveTool(save_name = name)
    """
    __implementation__ = JS_CODE_SAVE
    save_name = String()

def binary(x):
    '''Convert int to binary and return indices of bits that are 1'''
    bi = list(bin(x)[2:])[::-1]
    indices = np.where(np.array(bi) == "1")[0]
    return indices

def map_indices(x):
    '''Return list of notifications based on binary of the given int'''
    indices = binary(x)
    notification_mask = {0:"sock off",
                          1:"movement",
                          2:"buffer reset",
                          3:"HR out of range",
                          4:"signal saturating DC amplifier",
                          5:"signal saturating DC amplifier",
                          6:"signal saturating DC amplifier",
                          7:"signal saturating DC amplifier",
                          8:"signal saturating DC amplifier",
                          9:"signal saturating DC amplifier",
                          10:"DC signal low",
                          11:"LED adjusting",
                          12:"low pulse amplitude",
                          13:"AC Ambient Signal is Too High",
                          14:"O2 out of range",
                          15:"Invalid HR"}
    notifications = []
    for i in range(len(indices)):
        # Find out which flags are active
        notifications.append(notification_mask[indices[i]])
    if len(notifications) == 0:
        return ["Good"]
    return list(set(notifications))

def get_file_names(dsn):
    file_names = []
    # Story_data is the folder that contains all day folders
    for directory, subdirectories, files in os.walk('Story_data'):
        for filename in files:
            if filename.find(dsn) != -1:
                file_names.append(os.path.join(directory, filename))
    return sorted(file_names)


def dsn_date(file, all_dates, state3=False):
    '''Return dataframe with the data from the given dsn and dates'''
    df = pd.read_csv(file, compression='gzip')
    df.columns = content

    # Load second file if there is one & append to df
    file2 = "{} copy{}".format(file[:-3], file[-3:])
    if file2 in set(all_dates):
        df2 = pd.read_csv(file2, compression='gzip')
        df = df.append(df2, sort=True)

    df = df.drop_duplicates()
    df.timestamp = pd.to_datetime(df.timestamp, unit='s')
    df = df.sort_values(by=['timestamp'])
    if state3:
        return df
    return df[df.base_state > 3]

def get_source(df, names):
    '''Put all data needed for plotting into a dictionary'''
    def datetime(x):
        '''Function to format the datetime data'''
        return np.array(x, dtype=np.datetime64)

    maxs = names.copy()
    maxs.remove("movement_raw")
    maxs.remove("skin_temperature")

    # Find the hight for the plot (tall enough so the tooltip doesnt cover data)
    max_hr = df[maxs].max().max()
    min_val = df[maxs].min().min()
    height = 12*(len(names)+1)
    horizontal_points = [max_hr + height]*df.shape[0]

    good_data = data_to_plot(df[df.notification_mask == 0], names[:3])
    bad_data = data_to_plot(df[df.notification_mask != 0], names[:3])

    base_mvmt_data = ["xs", "base_state", "movement_raw"]
    base_mvmt = data_to_plot(df, base_mvmt_data[1:])

    # Where data is stored so it can be displayed in the tooltip
    source_data = {
        'horizontal'         : horizontal_points,
        'date'               : datetime(df['timestamp']),
        'notification_mask' : df.notification_mask #.apply(map_indices),
    }
    source_data.update({names[i] : df[names[i]] for i in range(len(names))})
    source_data["skin_temperature"] = df["skin_temperature"]/2
    source_data1 = {'plot_' + base_mvmt_data[i] : base_mvmt[i] for i in range(len(base_mvmt_data))}

    source_data2 = {'good_x' : good_data[0]}
    source_data2.update({'good_' + names[i] : good_data[i+1] for i in range(3)})
    source_data3 = {'bad_x' : bad_data[0]}
    source_data3.update({'bad_' + names[i] : bad_data[i+1] for i in range(3)})

    nine = start_indices(df, 9)
    ten = start_indices(df, 10)
    # combine indices for 9s and 10s to get yellows
    yellow = np.insert(ten, 0, nine)
    red = start_indices(df, 12)

    source_data4 = {'yellow' : [[df.iloc[i].timestamp]*20 for i in yellow]}
    source_data4.update({'ys' : [np.linspace(0,500,20) for _ in yellow]})

    source_data5 = {'red' : [[df.iloc[i].timestamp]*20 for i in red]}
    source_data5.update({'red_ys' : [np.linspace(0,500,20) for _ in red]})

    return source_data, source_data1, source_data2, source_data3, source_data4, source_data5, min_val, max_hr

def start_indices(df, x):
    "Returns the indices where the base state changes to x"
    # Find non consecutive instances of base state x
    value = df.base_state.eq(x)
    indices = np.ndarray.flatten(np.argwhere(value))
    if len(indices) == 0:
        return indices
    differences = np.diff(indices)
    differences = np.insert(differences, 0, 0)
    final_indices = list(np.ndarray.flatten(np.argwhere(differences != 1)))
    return indices[final_indices]

def data_to_plot(df, save):
    '''Split the data based on consecutive readings'''
    data = [[] for i in range(len(save)+1)]
    remove = 0
    d = pd.Timedelta(2, 's')
    while df.shape[0] != 0:

        consecutive = df.timestamp.diff().fillna(0).abs().le(d)

        idx_loc = df.index.get_loc(consecutive.idxmin())
        if idx_loc == 0:
            df_to_plot = df
            df = df.iloc[0:0] # empty the df
        else:
            df_to_plot = df.iloc[:idx_loc]
            remove = df_to_plot.shape[0]
            df = df.iloc[remove:]

        data[0].append(df_to_plot.timestamp)
        for i in range(len(save)):
            if save[i] == "skin_temperature":
                data[i+1].append(df_to_plot[save[i]]/2)
            elif save[i] == "base_state":
                data[i+1].append(df_to_plot[save[i]]*10)
            elif save[i] == "movement_raw":
                data[i+1].append(df_to_plot[save[i]]/5)
            else:
                data[i+1].append(df_to_plot[save[i]])

    return data

def plot_data(df, dsn):
    '''Plot the data in the given dataframe

    Parameters:
        df        (dataframe) - data from the given dsn
        dsn       (str) - device identifier

    '''
    names = ["heart_rate_raw", "oxygen_raw", "skin_temperature", "base_state", "movement_raw"]
    colors = ["red", "blue", "orange", "purple", "green"]#["#F70025", "#34888C", "orange", "purple", "gray"]
    alphas = [.8,8,.8,.6,.5]

    # Where data is stored so it can be displayed and changed dynamically
    source_data, source_data1, source_data2, source_data3, source_data4, source_data5, min_val, max_hr = get_source(df, names)

    # Multiple sources because there are different lengths of data
    source = ColumnDataSource(data=source_data)
    source1 = ColumnDataSource(data=source_data1)
    source2 = ColumnDataSource(data=source_data2)
    source3 = ColumnDataSource(data=source_data3)
    source4 = ColumnDataSource(data=source_data4)
    source5 = ColumnDataSource(data=source_data5)

    # Build plot tools
    hover_tool = HoverTool(
        tooltips=[
        ( 'time',   '@date{%T}' ),] +
        [(name, '@{}'.format(name)) for name in names] +
        [('notification', '@notification_mask')],
        formatters={'date'  : 'datetime',}, # use default 'numeral' formatter for other fields
        mode='vline', renderers=[]
    )
    crosshair = CrosshairTool(dimensions='height', line_alpha=.6)
    box_zoom = BoxZoomTool(dimensions='width')
    zoom_out = ZoomOutTool(dimensions='width', factor=.5)
    save = CustomSaveTool(save_name=dsn)

    x_range_start = df.timestamp.min() - timedelta(minutes=30)
    x_range_end = df.timestamp.max() + timedelta(minutes=30)

    # Create figure; use webgl for better rendering
    tools=[save, box_zoom, 'xpan', zoom_out, hover_tool, crosshair]
    p = figure(width=950, height=500, title="{} Data".format(dsn), x_axis_type="datetime",
           tools=tools, toolbar_location="above", x_range=(x_range_start, x_range_end),
           y_range=(0,max_hr+(24*(len(names)+1))), output_backend='webgl')

    # To have the Legend outside the plot, each line needs to be added to it
    legend_it = []

    for i in range(len(names)):
        legend_line = p.line(x=df.timestamp.iloc[-1:], y=0, color=colors[i], alpha=1,line_width=2)
        if names[i] in ["movement_raw", "base_state"]:
            legend_it.append((names[i], [legend_line, p.multi_line(xs='plot_xs', ys='plot_'+names[i], color=colors[i], alpha=alphas[i], source=source1)]))
        else:
            bad_data_line = p.multi_line(xs='bad_x', ys='bad_'+names[i], color=colors[i], alpha=.1, source=source3)
            legend_it.append((names[i], [legend_line, p.multi_line(xs='good_x', ys='good_'+names[i], color=colors[i], alpha=alphas[i], source=source2), bad_data_line]))

    legend_it.append(("Yellow notifications", [p.multi_line(xs='yellow', ys='ys', color='#F5BE41', line_dash='dashed', line_width=1.5, source=source4)]))
    legend_it.append(("Red notifications", [p.multi_line(xs='red', ys='red_ys', color='red', line_dash='dashed', source=source5)]))

    # Creating a location for the tooltip box to appear (so it doesn't cover the data)
    horizontal_line = p.line(x='date', y='horizontal', color='white', alpha=0, source=source)
    hover_tool.renderers.append(horizontal_line)

    p.xaxis.axis_label = 'Time'
    p.xaxis.formatter=DatetimeTickFormatter(
            days=["%m/%d %T"],
            months=["%m/%d %T"],
            hours=["%m/%d %T"],
            minutes=["%m/%d %T"],
            seconds=["%m/%d %T"],
            minsec=["%m/%d %T"],
            hourmin=["%m/%d %T"]
    )

    legend = Legend(items=legend_it)
    legend.click_policy="hide"    # Hide lines when they are clicked on
    p.add_layout(legend, 'right')
    return p, source, source1, source2, source3, source4, source5

def update_data(p, source, source1, source2, source3, source4, source5, df, dsn, all_dates, date):
    '''Get new dataframe when the dsn or date is changed'''
    names = ['heart_rate_raw', 'oxygen_raw', 'skin_temperature', 'base_state', 'movement_raw']
    if dsn != all_dates[0][20:35]:
        all_dates = get_file_names(dsn)
    # all_dates at a certain date
    file = "Story_data/{}{}{}/{}.csv.gz".format(date[:4], date[5:7], date[8:], dsn)
    if file not in set(all_dates):
        print("No data for {}".format(date))
        return df
    df = dsn_date(file, all_dates)

    # This is how the plot is changed:
    source.data, source1.data, source2.data, source3.data, source4.data, source5.data, min_val, max_hr = get_source(df, names)

    # change x/y axis range:
    p.y_range.start = max(0,min_val-10)
    p.y_range.end = max_hr+(24*(len(names)+1))

    p.x_range.start = df.timestamp.min() - timedelta(minutes=30)
    p.x_range.end = df.timestamp.max() + timedelta(minutes=30)


def set_up_widgets(p, source, source1, source2, source3, source4, source5, df, all_dates, text_dsn):
    '''Set up widgets needed after an initial dsn is entered'''
    dsn = text_dsn.value
    # Set up widgets
    text_title = TextInput(title="Title:", value="{} Data".format(dsn))
    text_save = TextInput(title="Save As:", value=dsn)

    min_day = date_of_file(all_dates[0])
    max_day = date_of_file(all_dates[-1])
    plus_one = max_day + timedelta(days=1)

    calendar = DatePicker(title="Day:", value=date(plus_one.year, plus_one.month, plus_one.day),
            max_date=max_day, min_date=min_day)
    button = Button(label="Update", button_type="success")

    columns = [
        TableColumn(field="day", title="Date", formatter=DateFormatter(format="%m/%d/%Y")),
        TableColumn(field="hr", title="Avg HR", formatter=NumberFormatter(format="0.0")),
        TableColumn(field="o2", title="Avg O2", formatter=NumberFormatter(format="0.0")),
        TableColumn(field="temp", title="Avg Temp", formatter=NumberFormatter(format="0.0"))
    ]

    # Set up callbacks
    def update_title(attrname, old, new):
        p.title.text = text_title.value

    def update_save(attrname, old, new):
        p.tools[0].save_name = text_save.value

    def update():
        text_dsn.value = text_dsn.value.strip(" ")  # Get rid of extra space

        update_data(p, source, source1, source2, source3, source4, source5, df, text_dsn.value, all_dates, date=str(calendar.value))

        # Title/save update dsn
        text_title.value = text_dsn.value + " Data"
        text_save.value = text_dsn.value

    text_title.on_change('value', update_title)
    text_save.on_change('value', update_save)

    button.on_click(update)

    # Set up layouts and add to document
    inputs = widgetbox(text_title, text_save, calendar, button)

    curdoc().add_root(row(inputs, p, width=1300))

def date_of_file(filename):
    day = filename[11:19]
    datetime_format = date(int(day[0:4]), int(day[4:6]), int(day[6:]))  + timedelta(days=1)
    return datetime_format

with open("column_names.txt") as f:
    content = f.readlines()
content = content[0].split(',')

text_dsn = TextInput(title="DSN:")
dsn_button = Button(label="Update DSN", button_type="success")
curdoc().add_root(row(text_dsn))

def dsn_text_update(attrname, old, new):
    all_dates = get_file_names(text_dsn.value)
    most_recent = all_dates[-1] # already sorted
    df = dsn_date(most_recent, all_dates)

    # df must not be empty
    if df.shape[0] == 0:
        df = dsn_date(most_recent, all_dates, True) # There is only charging data on most recent day
    p, source, source1, source2, source3, source4, source5 = plot_data(df, text_dsn.value)
    text_dsn.remove_on_change('value', dsn_text_update)
    set_up_widgets(p, source, source1, source2, source3, source4, source5, df, all_dates, text_dsn)

text_dsn.on_change('value', dsn_text_update)
