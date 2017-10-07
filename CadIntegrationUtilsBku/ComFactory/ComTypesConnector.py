# Copyright (c) 2017 Thomas Karl Pietrowski

# Comtypes modules
import comtypes
import comtypes.client
import ctypes

class ComConnector:
    def CreateClassObject(app_name):
        return comtypes.client.GetClassObject(app_name).CreateInstance()

    def CoInit():
        comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)

    def UnCoInit():
        comtypes.CoUninitialize()
    
    def GetComObject(toBeObjected):
        return toBeObjected._comobj
    
    @property
    def IntByRef(self):
        int_value = ctypes.c_int()
        return ctypes.byref(int_value)
