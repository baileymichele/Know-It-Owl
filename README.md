# Plot Sample Data with Bokeh

This information will explain how to use the provided bokeh plotting tools for Owlet Smart Sock data. A small sample dataset is provided to get a idea of how the tool works

## Getting Started

These instructions will explain what is needed in order to use the bokeh plotting tool using sample data given.

### Prerequisites

First, download all files provided.

### Installing

Note that these tools run using python 3.6.

In order to use the bokeh plotting tool for plot_local_data.py, the following packages need to be installed:

    numpy
    pandas
    bokeh (version 1.0.1)
    selenium
    phantomjs
    pillow
    nodejs

First, you can install the specific version of bokeh using the conda command:

```
conda install bokeh=1.0.1
```

All packages can be installed at the same time by separating them by a space after the "install" command. For example, to install using conda run the following:

```
conda install numpy pandas bokeh=1.0.1 selenium phantomjs pillow nodejs
```

To install bokeh and selenium using pip, run:

```
pip install numpy pandas bokeh=1.0.1 selenium phantomjs pillow nodejs
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
