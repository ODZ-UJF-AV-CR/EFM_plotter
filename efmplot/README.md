# UST THUNDERMILL01 data manager

## efmplot.py

`efmplot.py` is a tool for visualizing and saving data from the THUNDERMILL01 EFM mill. This tool enables real-time data visualization through a graphical interface, and can also send data via websocket for remote monitoring through a web interface.


### Features

- **Graphical User Interface (GUI):** Allows users to interactively work with and visualize data in a graphical form.
- **Serial Port Data Reading:** Electric field data is acquired via a serial connection.
- **Websocket Mode:** Provides the ability to remotely send data through a websocket stream. `efmplot` acts as a websocket server.


### Installation

For `efmplot.py` to function correctly, Python 3 and several dependencies listed in `requirements.txt` are required.

### Usage

`efmplot` can be run with the following arguments according to user needs:

```bash
python3 efmplot.py --gui  # Launches the application with a graphical interface
python3 efmplot.py --port /dev/ttyUSB0  # Reads data from a serial port
python3 efmplot.py --websocket  # Activates websocket mode
```

##### Start-up examples 

Headles mode:
```
python3 efmplot.py --port /dev/ttyUSB1 --websocket
```

GUI mode with websockets
```
python3 efmplot.py --port /dev/ttyUSB0 --websocket --gui
```

#### Arguments

- `--gui`: Launches the application in a graphical interface for interactive data visualization.
- `--port`: Specifies the serial port for reading data (default is `/dev/ttyUSB0`).
- `--websocket`: Enables websocket mode, allowing real-time data transmission.

Arguments can be used simultaneously.


## Gui 

The application includes a simple GUI interface that enables the visualization of data from the mill on the computer monitor to which it is connected. In the created window, there is a graph displaying the progression of a single rotation of the mill.

![image](https://github.com/ODZ-UJF-AV-CR/EFM_plotter/assets/5196729/a60c6c2b-4fee-4108-8bca-53235f57e41a)


## Web interface

EFMPLOT includes a websocket server that allows remote connections for displaying real-time values. 


One example is a [simple HTML](./index.html) page that can be viewed in a web browser.
![image](https://github.com/ODZ-UJF-AV-CR/EFM_plotter/assets/5196729/ed06f64c-c002-4d3d-9507-e8e27992453e)
