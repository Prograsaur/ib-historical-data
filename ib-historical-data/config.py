#!/usr/bin/env python
#-----------------------------------------------------------------------------
# Author: Sergey Ishin (Prograsaur) (c) 2018
#-----------------------------------------------------------------------------

'''
Interactive Brokers TWS API -- Historical data loader

Configuration file
'''

import logging

class Config: pass

config = Config()

# Logging
config.logpath = 'log'
config.loglevel = logging.INFO

# TWS Connection
config.twsport = 7497
config.clientId = 0
