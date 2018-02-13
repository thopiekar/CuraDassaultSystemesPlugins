'''
Created on 01.02.2018

@author: Thomas Pietrowski
'''
import os
from SystemUtils import convertDosPathIntoLongPath # @UnresolvedImport

executable_extension = ".exe"
sldwks_exe = "D:\\Program Files\\SOLIDWORKS\\SLDWORKS.exe \"%1\""
sldwks_exe = sldwks_exe[:sldwks_exe.find(executable_extension)+len(executable_extension)+1]
sldwks_exe = convertDosPathIntoLongPath(sldwks_exe)
sldwkd_inst = os.path.split(sldwks_exe)[0]

print(sldwkd_inst)