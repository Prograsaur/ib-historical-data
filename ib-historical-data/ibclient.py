#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Author: Sergey Ishin (Prograsaur) (c) 2018
#-----------------------------------------------------------------------------

'''
Interactive Brokers TWS API -- Historical data loader

Interactive Brokers Client class.

Client has to check not just messages from the TWS but messages from the GUI as well.
To do so I just copied the EClient.run() method body from the API code and
added onLoopIteration() hook call inside the EClient infinite loop.
I will use this hook to process messages from other sources (GUI), not just TWS.

Uncomment self.onIdle() to create another hook to process something while
no messages are comming from the TWS.
'''

#region import
import traceback
import logging
import queue

from ibapi import (decoder, reader, comm)
from ibapi.client import EClient
from ibapi.common import *
from ibapi.utils import BadMessage
#endregion import

class IBClient(EClient):
    def __init__(self, wrapper):
        EClient.__init__(self, wrapper)

    def run(self):
        """
        This is the function that has the message loop.

        Extended copy of the EClient run()
        + onLoopIteration() hook
        + onIdle() hook
        """
        try:
            while not self.done and (self.isConnected()
                        or not self.msg_queue.empty()):
                try:
                    try:
                        # Hook to process messages/events from other sources.
                        self.onLoopIteration()
                        text = self.msg_queue.get(block=True, timeout=0.2)
                        if len(text) > MAX_MSG_LEN:
                            self.wrapper.error(NO_VALID_ID, BAD_LENGTH.code(),
                                "%s:%d:%s" % (BAD_LENGTH.msg(), len(text), text))
                            self.disconnect()
                            break
                    except queue.Empty:
                        # Hook to process something while no messages are
                        # comming from the TWS.
                        # self.onIdle() 
                        logging.debug("queue.get: empty")
                    else:
                        fields = comm.read_fields(text)
                        logging.debug("fields %s", fields)
                        self.decoder.interpret(fields)
                except (KeyboardInterrupt, SystemExit):
                    logging.info("detected KeyboardInterrupt, SystemExit")
                    self.keyboardInterrupt()
                    self.keyboardInterruptHard()
                except BadMessage:
                    logging.info("BadMessage")
                    self.conn.disconnect()
                except Exception:
                    logging.error(traceback.format_exc())
                logging.debug("conn:%d queue.sz:%d",
                             self.isConnected(),
                             self.msg_queue.qsize())
        finally:
            self.disconnect()

    def onLoopIteration(self):
        pass

#    def onIdle(self):
#        pass

#region main
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    print(__doc__)
    print('This is a python library - not standalone application')
    sys.exit(-1)
#endregion main
 