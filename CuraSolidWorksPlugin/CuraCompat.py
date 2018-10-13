from UM.Application import Application # @UnresolvedImport
from UM.Version import Version

class Deprecations:
    def getPreferences():
        if Version("3.3") <= Version(Application.getInstance().getVersion()):
            return Application.getInstance().getPreferences()
        else:
            return Preferences.getInstance()

class ApplicationCompat():
    def __init__(self):
        # TODO: Adding this to a compat layer
        if Version("3.3") <= Version(Application.getInstance().getVersion()):
            self.qml_engine = Application.getInstance()._qml_engine
        else:
            self.qml_engine = Application.getInstance()._engine
