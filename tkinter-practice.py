import numpy as np
import time

import tkinter as tk
from tkinter import *
from tkinter.ttk import Notebook, Sizegrip, Separator
from tkinter.font import Font, BOLD

import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class App():
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sample MGR GUI")
        self.root.geometry('1000x700')

        self.grid_width = 150
        self.grid_height = 100

        self.f = plt.figure(1)
        self.a = self.f.add_subplot(111)

        self.xdata = []
        self.ydata = []

        self.index = 0

        # Make some default fonts
        self.bold16 = Font(self.root, family="Helvetica", size=16, weight=BOLD)

        # make some frames to put stuff in
        frame1 = Frame(self.root)
        frame3 = Frame(self.root, bg="purple")

        # make some buttons! One toggles the other on/off, example of how to disable buttons 
        # and do callbacks with arguments
        b1 = self.pack_button(frame3, callback=None, loc='bottom')
        b2 = self.pack_button(frame3, callback=lambda: self.toggle_button(b1), loc='bottom', text="I toggle the other button")
        
        # separator = Separator(frame2, orient=VERTICAL)
        # separator.pack(side='left', expand=True, fill=Y, anchor=W, ipadx=2.5, before=b2)

        # make the (2x4) grid and make it stretchy if the window is resized, 
        # with all the columns and rows stretching by the same weight
        self.make_status_grid(frame1)
        frame1.columnconfigure([0,1], weight=1, minsize=self.grid_width)
        frame1.rowconfigure([0,1,2,3], weight=1, minsize=self.grid_height)

        # add a notebook
        self.make_data_stream(frame3)

        # add a sizegrip to the bottom
        sizegrip = Sizegrip(self.root)
        sizegrip.pack(side="bottom", expand=False, fill=BOTH, anchor=SE)

        # pack the frames
        frame1.pack(side="left", expand=True, fill=BOTH)
        frame3.pack(side="right", expand=True, fill=BOTH)

        
    ## --------------------- LAYOUT --------------------- ##
    
    def make_frame(self, root, loc, color:str="white"):
        frame = Frame(root, bg=color)
        # frame.pack(side=loc, expand=True, fill=BOTH)
        return frame
    
    def pack_button(self, root, callback, loc:str="right", text="I'm a button :]"):
        """General method that creates and packs a button inside the given root"""
        button = Button(root, text=text, command=callback)
        button.pack(side=loc)
        return button
    
    def plot_xy(self):
        fig = plt.figure(1)
        # plt.ion()
        t = np.arange(0.0,3.0,0.01)
        s = np.sin(np.pi*t)
        plt.plot(t,s)
        return fig

    def animate(self, i):
        pullData = open("sampleText.txt","r").read()
        dataList = pullData.split('\n')
        xList = []
        yList = []
        for eachLine in dataList[0:self.index]:
            if len(eachLine) > 1:
                x, y = eachLine.split(',')
                xList.append(int(x))
                yList.append(int(y))

        self.a.clear()
        self.a.plot(xList, yList)
        self.index += 1
    
    def make_data_stream(self, root):
        tabs = ["All", "Picarro Spectroscopy", "Laser Distance Sensor", "Abakus Particle Counter",
                       "MFC Flow Meter", "Bronkhurst Pressure", "Melthead"]
        
        notebook = Notebook(root)

        for i, tab in enumerate([tabs[0]]):
            window = Frame(notebook)
            window.grid()
            label = Label(window, text=tab+" data", font=self.bold16)
            label.grid(column=0, row=0)
            
            canvas = FigureCanvasTkAgg(self.f, window)
            canvas.draw()
            time.sleep(0.1)
            canvas.get_tk_widget().grid(row=1, column=0) 

            notebook.add(window, text=tab)

        notebook.pack(padx = 5, pady = 5, expand = True)
   
    def make_status_grid_cell(self, root, col, row, colspan=1, rowspan=1, color='white'):
        """Method to make one frame of the grid at the position given"""        
        frame = Frame(root, relief='ridge', borderwidth=2.5, bg=color, highlightcolor='blue')
        # place in the position we want and make it fill the space (sticky)
        frame.grid(column=col, row=row, columnspan=colspan, rowspan=rowspan, sticky='nsew')
        # make it stretchy if the window is resized
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        return frame 
    
    def make_status_grid(self, root):
        """Makes a grid of all the sensors. Currently a placeholder for anything we 
        want to display about the instruments, like adding control or their status"""
        self.start_all_frame = self.make_status_grid_cell(root, col=0, row=0, colspan=2)
        label=Label(self.start_all_frame, text="Start All Data Collection")
        label.grid(row=0, column=0)

        self.picarro_frame = self.make_status_grid_cell(root, col=0, row=1)
        label=Label(self.picarro_frame, text="Picarro", justify='center')
        label.grid(row=0, column=0)

        self.laser_frame = self.make_status_grid_cell(root, col=1, row=1)
        label=Label(self.laser_frame, text="Laser Distance")
        label.grid(row=0, column=0)

        self.abakus_frame = self.make_status_grid_cell(root, col=0, row=2)
        label=Label(self.abakus_frame, text="Abakus Particle Counter")
        label.grid(row=0, column=0)

        self.flow_frame = self.make_status_grid_cell(root, col=1, row=2)
        label=Label(self.flow_frame, text="Flow Meter")
        label.grid(row=0, column=0)

        self.bronkhorst_frame = self.make_status_grid_cell(root, col=0, row=3)
        label=Label(self.bronkhorst_frame, text="Bronkhorst")
        label.grid(row=0, column=0)

        self.melthead_frame = self.make_status_grid_cell(root, col=1, row=3)
        label=Label(self.melthead_frame, text="Melthead")
        label.grid(row=0, column=0)
        
    
    ## --------------------- CALLBACKS --------------------- ##
    
    def toggle_button(self, button: Button):
        """Method that toggles a button between its 'normal' state and its 'disabled' state"""
        if button["state"] == NORMAL:
            button["state"] = DISABLED
        else:
            button["state"] = NORMAL

    def run(self):
        ani = FuncAnimation(self.f, self.animate, interval=1000)
        self.root.mainloop()
        self.root.destroy()

if __name__ == "__main__":
    app = App()
    app.run()