import winreg

class Test():
    def __init__(self):
        self._default_app_name = "SldWorks.Application"
    
    def getVersionedInstallationsFromRrgistry(self):
        versions = []
        registered_services = winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, None)
        key_prefix = "{}.".format(self._default_app_name)
        i = 0
        while True:
            try:
                key = winreg.EnumKey(registered_services, i)
                if key.startswith(key_prefix):
                    try:
                        major_version = key[len(key_prefix):]
                        major_version = int(major_version)
                        versions.append(major_version)
                    except ValueError:
                        pass
                i += 1
            except WindowsError: 
                break
        return versions

if __name__ == "__main__":
    print(Test().getVersionedInstallationsFromRrgistry())