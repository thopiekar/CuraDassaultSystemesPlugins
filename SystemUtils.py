# Copyright (c) 2017 Thomas Karl Pietrowski

#import ctypes
import win32api

def convertDosPathIntoLongPath(dosPath):
    # TODO: Move the code into the COM compat layer!
    #longpath = ctypes.create_unicode_buffer(1024)
    #if not ctypes.windll.kernel32.GetLongPathNameW(dosPath, longpath, 1024): # GetLongPathNameW: @UndefinedVariable
    #    # This basically indicates that the call of the function failed, since nothing has been passed to the buffer.
    #    # It is better to catch these situations and raise an error here!
    #    raise ValueError("Bad path passed!")
    #return longpath.value
    longpath = win32api.GetLongPathName(dosPath)
    return longpath
