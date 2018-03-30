#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Author: Sergey Ishin (Prograsaur) (c) 2018
#-----------------------------------------------------------------------------

'''
Interactive Brokers TWS API -- Historical data loader

Notes:
TWS API Guide http://interactivebrokers.github.io/tws-api/#gsc.tab=0

To setup the button IB TWS side app:
1) File => Global configuration...
    Configuration => API => Settings
    x Enable ActiveX and Socket Clients
    o Read-Only API
    x Download open orders on connection
    Socket Port: 7497
    x Expose entire trading schedule to API
    x Let API account requests switch user-visible account subscription
    Master API client ID: 0
    x Allow connections from the localhost only
'''

#region import
import sys
import multiprocessing as mp
import queue
import logging

from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import BarData, TickerId

from config import config
from gui import runGui
from logutils import init_logger
from ibclient import IBClient
#endregion import

def makeSimpleContract(symbol, secType = "STK", currency = "USD", exchange = "SMART"):
    contract = Contract()
    contract.symbol=symbol
    contract.secType=secType
    contract.currency=currency
    contract.exchange=exchange

    return contract


class App(IBClient, EWrapper):
    """
    Mixin of Client (message sender and message loop holder)
    and Wrapper (set of callbacks)
    """
    def __init__(self, gui2tws, tws2gui):
        EWrapper.__init__(self)
        IBClient.__init__(self, wrapper=self)

        self.gui2tws = gui2tws
        self.tws2gui = tws2gui
        self.nKeybInt = 0
        self.started = False
        self._lastId = None
        self._file = None

    @property
    def nextId(self):
        self._lastId += 1
        return self._lastId

    def keyboardInterrupt(self):
        """Callback - User pressed Ctrl-C"""
        self.nKeybInt += 1
        if self.nKeybInt == 1:
            msg = "Manual interruption!"
            logging.warn(msg)
            print(msg)
            self._onStop()
        else:
            msg = "Forced Manual interruption!"
            logging.error(msg)
            print(msg)
            self.done = True

    def _onStart(self):
        if self.started: return
        self.started = True
        self.onStart()

    def _onStop(self):
        if not self.started: return
        self.onStop()
        self.started = False

#region GuiMsgProcessors
#----------------------------------------------------------------------------

    def exit(self):
        """
        Exit from the application
        """
        self.done = True
        self._onStop()

#endregion GuiMsgProcessors

#region Callbacks
#----------------------------------------------------------------------------

    def onStart(self):
        logging.info('Main logic started')

    def onStop(self):
        if self._file: self._file.close()
        logging.info('Main logic stopped')

    def onLoopIteration(self):
        logging.debug('onLoopIteration()')
        try:
            msg = self.gui2tws.get_nowait()
            logging.info(f'GUI MESSAGE: {msg}')
            if msg.startswith('SAVE '):
                if self._file:
                    logging.error('Previuos work is still in progress.')
                msg = msg[5:] # Skip 'SAVE '

                symbol, endDate, duartion, barSize, barType, fileName = msg.split('|')
                if ' ' not in endDate: endDate += ' 00:00:00'

                self._file = open(fileName, 'w')
                self._write('Date, Time, Open, Close, Min, Max, Trades, Volume, Average')

                self.reqHistoricalData(self.nextId, makeSimpleContract(symbol),
                                      endDate, duartion, barSize, barType, 1, 1, False, [])

                # TODO Add message processing here
                pass
            elif msg == 'EXIT':
                self.exit()
            else:
                logging.error(f'Unknown GUI message: {msg}')
        except queue.Empty:
            pass

        self.count = 0

    def _write(self, msg):
        if self._file:
            self._file.write(msg)
            self._file.write('\n')
        else:
            print(msg)

    def nextValidId(self, orderId: int):
        """
        Callback
        orderId -- First unused order id provided by TWS
        Use reqIds() to request this info
        """
        EWrapper.nextValidId(self, orderId)
        logging.debug(f'Setting next order Id: {orderId}')

        self._lastId = orderId - 1
        self._onStart()

    def historicalData(self, reqId: int, bar: BarData):
        """ returns the requested historical data bars

        reqId    - the request's identifier
        date     - the bar's date and time (either as a yyyymmss hh:mm:ss
                   formatted string or as system time according to the request)
        open     - the bar's open point
        high     - the bar's high point
        low      - the bar's low point
        close    - the bar's closing point
        volume   - the bar's traded volume if available
        barCount - the number of trades during the bar's timespan (only available for TRADES).
        average  - the bar's Weighted Average Price
        hasGaps  - indicates if the data has gaps or not. """

        EWrapper.historicalData(self, reqId, bar)
        
        date, time = bar.date.split()
        self._write(f'{date},{time},{bar.open},{bar.close},{bar.low},{bar.high},{bar.barCount},{bar.volume},{bar.average}')
        self.tws2gui.put('NEWROW')

    def historicalDataEnd(self, reqId:int, start:str, end:str):
        """ Marks the ending of the historical bars reception. """
        EWrapper.historicalDataEnd(self, reqId, start, end)
        if self._file:
           self._file.close()
           self._file = None
        self.tws2gui.put('END')

    def error(self, reqId:TickerId, errorCode:int, errorString:str):
        """This event is called when there is an error with the
        communication or when TWS wants to send a message to the client."""
        EWrapper.error(self, reqId, errorCode, errorString)

        # Error messages with codes (2104, 2106, 2107, 2108) are not real errors but information messages
        if errorCode not in (2104, 2106, 2107, 2108): self.tws2gui.put(f'ERROR {errorCode}: {errorString}')

#endregion Callbacks

#region main
#-------------------------------------------------------------------------------
def main():
    init_logger('history', logpath=config.logpath, loglevel=config.loglevel)

    gui2tws = mp.Queue()
    tws2gui = mp.Queue()

    # Interactive Brokers TWS API has its own infinite message loop and
    # at least one additional thread.
    # Tkinter from its side “doesn’t like” threads and has an infinite loop as well.
    # To resolve this issue each component will run in the separate process

    gui = mp.Process(target=runGui, args=(gui2tws, tws2gui))
    gui.start()

    logging.info('The History Downloader started')

    app = App(gui2tws, tws2gui)
    app.connect('127.0.0.1', config.twsport, clientId=config.clientId)
    logging.info(f'Server version: {app.serverVersion()}, Connection time: {app.twsConnectionTime()}')
    app.run()

    gui.join()

    logging.info('The History Downloader stopped')
    return 0

if __name__ == "__main__":
    sys.exit(main())
#endregion main
