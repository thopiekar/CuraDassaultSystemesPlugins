import winreg

parentKey = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, None)
i = 0
while True:
    try:
        key = winreg.EnumKey(parentKey, i)
        if key.startswith("SldWorks.Application"):
            print(key)
        i += 1
    except WindowsError: 
        break