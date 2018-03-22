#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Author: Sergey Ishin (Prograsaur) (c) 2018
#-----------------------------------------------------------------------------

'''
Interactive Brokers TWS API -- Historical data loader
Logging utils
'''

#region import
import os
import sys
import time
import logging
#endregion import

#region Utils
#-----------------------------------------------------------------------------
_logLevel_table = {
    'CRITICAL' : logging.CRITICAL,
    'ERROR'    : logging.ERROR   ,
    'WARNING'  : logging.WARNING ,
    'INFO'     : logging.INFO    ,
    'DEBUG'    : logging.DEBUG   ,
    'NOTSET'   : logging.NOTSET  ,
    'NONE'     : logging.NOTSET  ,
}

def loglevel_to_int(loglevel):
    if isinstance(loglevel, int): return loglevel
    if loglevel.isdigit(): return int(loglevel)
    return _logLevel_table[loglevel.upper()]

def init_logger(suffix, logpath='log', loglevel=logging.INFO):
    loglevel = loglevel_to_int(loglevel)

    if not os.path.exists(logpath): os.makedirs(logpath)

    recfmt = '(%(threadName)s) %(asctime)s.%(msecs)03d %(levelname)s %(filename)s:%(lineno)d %(message)s'
    timefmt = '%Y-%m-%d %H:%M:%S'

    logging.basicConfig(filename=time.strftime(f'{logpath}/FS-{suffix}.%Y%m%d_%H%M%S.log'),
                        filemode="w",
                        level=loglevel,
                        format=recfmt, datefmt=timefmt)

    logger = logging.getLogger()
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    logger.addHandler(console)

    return logger
#endregion Utils

#region main
#-------------------------------------------------------------------------------
if __name__ == '__main__':
    print(__doc__)
    print('This is a python library - not standalone application')
    sys.exit(-1)
#endregion main
 