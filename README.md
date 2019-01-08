# Plot Sample Data with Bokeh

This information will explain how to use the provided bokeh plotting tools for Owlet Smart Sock data. A small sample dataset is provided to get a idea of how the tool works

## Getting Started

These instructions will explain what is needed in order to use the bokeh plotting tool using sample data given.

### Prerequisites

First, download all files provided.

### Installing

In order to use the bokeh plotting tool for plot_local_data.py, the following packages need to be installed:

    numpy
    pandas
    bokeh
    selenium
    phantomjs
    pillow
    nodejs

These packages can be installed at the same time by separating them by a space after the "install" command. For example, to install bokeh and selenium using pip run the following:

```
pip install bokeh selenium
```

To install bokeh and selenium using conda, run:

```
conda install bokeh selenium
```

## Running the tests

### Bokeh Server

To view the bokeh plot from a bokeh server, run a bokeh server in the terminal for the plot_local_data.py file. For example, from the directory where plot_local_data.py is stored, run:

```
bokeh serve plot_local_data.py
```

Then to view the plot in a browser, use the following URL:

```
http://localhost:5006/plot_local_data
```
