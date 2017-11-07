'''
Created on 3 nov. 2017

@author: t.pietrowski
'''

import comtypes.client

try:
    foo = comtypes.client.GetActiveObject("SldWorks.Application")
    was_active = True
except:
    foo = comtypes.client.CreateObject("SldWorks.Application")
    was_active = False

print(foo.RevisionNumber())

if not was_active:
    foo.ExitApp()