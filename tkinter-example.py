import tkinter as tk
from tkinter.ttk import Notebook, Sizegrip, Separator
from tkinter import *
from tkinter import Scrollbar
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import time

t_i = time.time()
big_data = {"Picarro Gas":{"time (epoch)":t_i, "data":{"CO2":0.0, "CH4":0.0, "CO":0.0, "H2O":0.0}},
                         "Picarro Water":{"time (epoch)":t_i, "data":{}},
                         "Laser Distance Sensor":{"time (epoch)":t_i, "data":{"distance (cm)":0.0, "temperature (°C)":99.99}},
                         "Abakus Particle Counter":{"time (epoch)":t_i, "data":{"bins":[0]*32, "counts/bin":[0]*32, "total counts":0}},
                         "Flowmeter SLI2000 (Green)":{"time (epoch)":t_i, "data":{"flow (uL/min)":0.0}},
                         "Flowmeter SLS1500 (Black)":{"time (epoch)":t_i, "data":{"flow (mL/min)":0.0}},
                         "Flowmeter":{"time (epoch)":t_i, "data":{"sli2000 (uL/min)":0.0, "sls1500 (mL/min)":0.0}},
                         "Bronkhurst Pressure":{"time (epoch)":t_i, "data":{}},
                         "Melthead":{"time (epoch)":t_i, "data":{}},
                        }

sensor_names = list(big_data.keys())

def make_data_stream_notebook(root):
    data_streaming_windows = []
    subplot_streaming_frames = []
    notebook = Notebook(root)
    for name in sensor_names:
        window = Frame(notebook)
        window.grid(column=0, row=0)
        notebook.add(window, text=name)

        data_streaming_windows.append(window)

        num_subplots = len(big_data[name]["data"].keys())
        for i in range(num_subplots):
            subplot_frame = Frame(window)
            subplot_frame.grid(column=0, row=i)
            subplot_streaming_frames.append(subplot_frame)

    notebook.pack(padx=2.5, pady=2.5, expand = True)
    return data_streaming_windows, subplot_streaming_frames


root = tk.Tk()
root.geometry('1400x700')
frame = tk.Frame(root)
frame.pack(side="right", expand=True, fill=BOTH)

data_streaming_windows, subplot_streaming_frames = make_data_stream_notebook(frame)

for i, window in enumerate(data_streaming_windows):
    fig = plt.figure(i)
    ax1 = fig.add_subplot(2,1,1)
    ax2 = fig.add_subplot(2,1,2)

    canvas = FigureCanvasTkAgg(fig, window)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=0)

root.mainloop()