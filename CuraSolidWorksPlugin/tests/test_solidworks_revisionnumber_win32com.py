'''
Created on 3 nov. 2017

@author: t.pietrowski
'''

import os

import win32com
win32com.__gen_path__ = os.path.join(os.path.split(__file__)[0], "gen_dir") 

import win32com.client

try:
    foo = win32com.client.GetActiveObject("SldWorks.Application")
    was_active = True
except:
    foo = win32com.client.Dispatch("SldWorks.Application")
    was_active = False

print(foo.RevisionNumber)

if not was_active:
    foo.ExitApp()