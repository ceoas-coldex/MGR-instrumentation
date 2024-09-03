import tkinter as tk
from tkinter import ttk

root = tk.Tk()

s = ttk.Style()
s.configure('TNotebook.Tab', font=('URW Gothic L','11','bold'))
s.layout("TNotebook", [])
# s.configure("TNotebook", tabmargins=0)

f = tk.Frame(root, bg='green')
f.configure(padx=100, pady=100)
f.grid()

notebook = ttk.Notebook(f)

f1 = tk.Frame(notebook, bg='red', width=200, height=200)
f2 = tk.Frame(notebook, bg='blue', width=200, height=200)

notebook.add(f1, text="frame 1" )
notebook.add(f2, text="frame 2 longer" )

notebook.grid(row=0, column=0, sticky="nw")
root.mainloop()