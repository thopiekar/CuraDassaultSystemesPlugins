# Copyright (c) 2017 Thomas Karl Pietrowski

# PyWin32 modules
import win32com.client
import win32com.client.gencache
import pythoncom
import pywintypes

class ComConnector:
    def CreateClassObject(app_name):
        return win32com.client.Dispatch(app_name)

    def CoInit():
        pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)

    def UnCoinit():
        pythoncom.CoUninitialize()

    def GetComObject(toBeObjected):
        return toBeObjected