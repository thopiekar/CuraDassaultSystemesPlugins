'''
Created on 30 sep. 2017

@author: t.pietrowski
'''

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

    def GetComObject(self, toBeObjected):
        return toBeObjected