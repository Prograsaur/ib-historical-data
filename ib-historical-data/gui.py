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
from tkinter import messagebox
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
    def value(self): return self.entry['text']

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

_duration2secs = dict(S=1, m=60, H=3600, D=3600*6.5, W=3600*6.5*5, M=3600*6.5*22, Y=3600*6.5*5*52)

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

    @property
    def seconds(self):
       return int(self.entry.get()) * _duration2secs[self.units.get()[0].upper()]

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

    @property
    def seconds(self):
        size = int(self.size.var.get())
        unit = self.units.var.get()
        if unit[:3] == 'min': return size * 60
        return size * _duration2secs[unit[0].upper()]

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
    def __init__(self, gui2tws, tws2gui):
        self.gui2tws = gui2tws
        self.tws2gui = tws2gui

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

        var = tki.IntVar()
        self.prgrs = ttk.Progressbar(root, mode='determinate', orient=tki.HORIZONTAL, variable=var)
        self.prgrs.var = var
        self.prgrs.grid(row=8, column=0, columnspan=3, sticky=tki.NSEW)
        var.set(0)

        self._onParamChange()

        root.columnconfigure(0, weight=0)
        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=0)

        root.protocol("WM_DELETE_WINDOW", self.onQuit)

        self.checkMsgFromTws()

    def _onParamChange(self, *args):
        self.file.value = (f'{self.endDate.value}-{self.symbol.value}-'
                           f'{self.duration.value}-{self.barSize.value}-'
                           f'{self.barType.value}.csv')

        self.save['state'] = ('disabled', 'normal')[bool(
            self.endDate.value and self.symbol.value and self.prgrs.var.get() == 0)]

    def checkMsgFromTws(self):
        try:
            while not self.tws2gui.empty():
                msg = self.tws2gui.get_nowait()
                if msg.startswith('ERROR'):
                    messagebox.showerror('TWS Error', msg)
                elif msg.startswith('NEWROW'):
                    self.prgrs.step()
                elif msg.startswith('END'):
                    self.prgrs.var.set(0)
                    self._onParamChange()
                else:
                    # TODO: Error here?
                    pass
                    logging.error(f'Unknown GUI message: {msg}')
        except queue.Empty:
            pass

        self.root.after(100, self.checkMsgFromTws)

    def run(self):
        self.init_gui()
        self.root.mainloop()

    def onQuit(self):
        from tkinter import messagebox
        if messagebox.askyesno("Quit", "Do you really want to quit?"):
            self.gui2tws.put('EXIT')
            self.root.destroy()

    def onSave(self):
        durSecs = self.duration.seconds
        barSecs = self.barSize.seconds
        lines = durSecs/barSecs
        if durSecs >= _duration2secs['W']: lines = int(lines*5/7)
        self.prgrs['maximum'] = lines
        self.prgrs.var.set(1)
        self._onParamChange()

        self.gui2tws.put(f'SAVE {self.symbol.value}|{self.endDate.value}|{self.duration.value}'
                       f'|{self.barSize.value}|{self.barType.value}|{self.path.value}/{self.file.value}')

def runGui(gui2tws, tws2gui):
    gui = Gui(gui2tws, tws2gui)
    gui.run()

#region main
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    print(__doc__)
    print('This is a python library - not standalone application')

#    runGui(gui2tws.Queue())
    sys.quit(-1)
#endregion main
 