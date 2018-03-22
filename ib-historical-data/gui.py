#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Author: Sergey Ishin (Prograsaur) (c) 2018
#-----------------------------------------------------------------------------

'''
Interactive Brokers TWS API -- Historical data loader

GUI module
'''
#region import
import sys
import tkinter as tki
from tkinter import filedialog
import tkinter.ttk as ttk

import queue
#endregion import

def addvar(widget, onChange, default):
    var = tki.StringVar()
    widget['textvariable'] = var
    widget.var = var
    var.set(default)
    var.trace_add(('write', 'unset'), onChange)
    return widget

class LabelEntry:
    def __init__(self, master, row, text, default, onChange):
        self.lbl = ttk.Label(master, text=text)
        self.entry = addvar(ttk.Entry(master), onChange, default)
        self.lbl.grid(row=row, column=0, sticky=tki.NW)
        self.entry.grid(row=row, column=1, columnspan=2, sticky=tki.NSEW)

    @property
    def value(self): return self.entry.get()

class FileName:
    def __init__(self, master, row, text, default=''):
        self.lbl = ttk.Label(master, text=text)
        self.entry = ttk.Label(master)
        self.lbl.grid(row=row, column=0, sticky=tki.NW)
        self.entry.grid(row=row, column=1, columnspan=2, sticky=tki.NSEW)

        self.value = default

    @property
    def value(self): return self.entry.get()

    @value.setter
    def value(self, v):
        self.entry['text'] = v

class Path:
    def __init__(self, master, row, text, default='/'):
        self.lbl = ttk.Label(master, text=text)
        self.entry = ttk.Entry(master)
        self.btn = ttk.Button(master, text='...', command=self._onSelectPath)
        self.lbl.grid(row=row, column=0, sticky=tki.NW)
        self.entry.grid(row=row, column=1, sticky=tki.NSEW)
        self.btn.grid(row=row, column=2, sticky=tki.NSEW)

        self.value = default

    def _onSelectPath(self):
        path = filedialog.askdirectory(parent=self.entry.master,
                                     initialdir=self.value,
                                     title='Please select the output folder')
        if path: self.value = path

    @property
    def value(self): return self.entry.get()

    @value.setter
    def value(self, v):
        self.entry.delete(0, tki.END)
        self.entry.insert(0, v)

class Duration:
    def __init__(self, master, row, text, onChange):
        self.lbl = ttk.Label(master, text=text)

        self.entry = addvar(ttk.Entry(master), onChange, '1')
        self.units = addvar(ttk.Combobox(master,
                            values='seconds day(s) week(s) month(s) year(s)'.split(),
                            state='readonly'), onChange, 'week(s)')
        self.lbl.grid(row=row, column=0, sticky=tki.NW)
        self.entry.grid(row=row, column=1, sticky=tki.NSEW)
        self.units.grid(row=row, column=2, sticky=tki.NSEW)

    @property
    def value(self): return f'{self.entry.get()} {self.units.get()[0].upper()}'

_barsize = dict(secs  = tuple('1 5 10 15 30'.split()),
                mins  = tuple('1 2 3 5 10 15 20 30'.split()),
                hours = tuple('1 2 3 4 8'.split()),
                day   = ('1',),
                week  = ('1',),
                month = ('1',))

_bartype = tuple('TRADES MIDPOINT BID ASK BID_ASK ADJUSTED_LAST HISTORICAL_VOLATILITY'
                ' OPTION_IMPLIED_VOLATILITY REBATE_RATE FEE_RATE YIELD_BID YIELD_ASK'
                ' YIELD_BID_ASK YIELD_LAST'.split())
class BarSize:
    def __init__(self, master, row, text, onChange):
        global _barsize

        self.lbl = ttk.Label(master, text=text)
        self.size = addvar(ttk.Combobox(master, values=_barsize['mins'], state='readonly'), onChange, '5')
        self.units = addvar(ttk.Combobox(master, values=tuple(_barsize.keys()), state='readonly'),
                            self._onUnitChange, 'mins')
    
        self.lbl.grid(row=row, column=0, sticky=tki.NW)
        self.size.grid(row=row, column=1, sticky=tki.NSEW)
        self.units.grid(row=row, column=2, sticky=tki.NSEW)
        self._onChange = onChange

    def _onUnitChange(self, *args):
        global _barsize
        size = self.size.var.get()
        unit = self.units.var.get()
        sizes = _barsize[unit]
        self.size['values'] = sizes
        self.size.var.set(size if size in sizes else sizes[0])
        self._onChange()

    @property
    def value(self):
        size = self.size.var.get()
        unit = self.units.var.get()
        if size == '1' and unit in ('mins', 'hours'):
            return f'1 {unit[:-1]}'
        return f'{size} {unit}'

class BarType:
    def __init__(self, master, row, text, onChange):
        self.lbl = ttk.Label(master, text=text)

        self.units = addvar(ttk.Combobox(master, values=_bartype, state='readonly'),
                           onChange, 'TRADES')
        self.lbl.grid(row=row, column=0, sticky=tki.NW)
        self.units.grid(row=row, column=1, columnspan=2, sticky=tki.NSEW)

    @property
    def value(self): return self.units.var.get()

class Gui:
    def __init__(self, queue):
        self.queue = queue

    def init_gui(self):
        root = self.root = tki.Tk()
        root.title("IB History Downloader")
        root.minsize(280, root.winfo_height())
        root.resizable(True, False)

        self.path = Path(root, 0, 'Output dir', './')
        self.file = FileName(root, 1, 'Output file', '')
        self.symbol = LabelEntry(root, 2, 'Symbol', '', self._onParamChange)
        self.endDate = LabelEntry(root, 3, 'End Date [Time]', '', self._onParamChange)
        self.duration = Duration(root, 4, 'Duration', self._onParamChange)
        self.barSize = BarSize(root, 5, 'Bar size', self._onParamChange)
        self.barType = BarType(root, 6, 'Data Type', self._onParamChange)

        self.save = ttk.Button(root, text='Save', command=self.onSave)
        self.save.grid(row=7, column=1, sticky=tki.NSEW)

        self.quit = ttk.Button(root, text='Quit', command=self.onQuit)
        self.quit.grid(row=7, column=2, sticky=tki.NSEW)

        self._onParamChange()

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=0)

        root.protocol("WM_DELETE_WINDOW", self.onQuit)

    def _onParamChange(self, *args):
        self.file.value = (f'{self.endDate.value}-{self.symbol.value}-'
                           f'{self.duration.value}-{self.barSize.value}-'
                           f'{self.barType.value}.csv')

    def run(self):
        self.init_gui()
        self.root.mainloop()

    def onQuit(self):
        from tkinter import messagebox
        if messagebox.askyesno("Quit", "Do you really want to quit?"):
            self.queue.put('EXIT')
            self.root.destroy()

    def onSave(self):
        self.queue.put('SAVE ')

def runGui(queue):
    gui = Gui(queue)
    gui.run()

#region main
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    print(__doc__)
    print('This is a python library - not standalone application')

#    runGui(queue.Queue())
    sys.quit(-1)
#endregion main
 