import tkinter as tk
from tkinter import *

class SampleApp(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        L1 = tk.Label(self, text="User Name")
        L1.pack(side = LEFT)
        E1 = Entry(self, bd =5)
        E1.pack(side = RIGHT)

    def rand_func(self, a, b, c):
        print("self:", self, "a:", a, "b:", b, "c:", c)
        print (a+b+c)

app = SampleApp()
app.mainloop()