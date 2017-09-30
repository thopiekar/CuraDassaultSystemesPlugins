# Copyright (c) 2017 Thomas Karl Pietrowski

# Uranium/Cura
from UM.Logger import Logger

# Trying to import one of the COM modules
try:
    from .ComTypesConnector import ComConnector
    Logger.log("i", "ComFactory: Using pywintypes!")
except ImportError:
    from .PyWin32Connector import ComConnector
    Logger.log("i", "ComFactory: Using comtypes!")