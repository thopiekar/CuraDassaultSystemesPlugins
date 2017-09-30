'''
Created on 30 sep. 2017

@author: t.pietrowski
'''

# Comtypes modules
import comtypes
import comtypes.client

class ComConnector:
    def CreateClassObject(app_name):
        return comtypes.client.GetClassObject(app_name).CreateInstance()

    def CoInit():
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)

    def UnCoInit():
        comtypes.CoUninitialize()
    
    def GetComObject(self, toBeObjected):
        return toBeObjected._comobj