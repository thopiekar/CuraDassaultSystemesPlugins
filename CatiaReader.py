# Copyright (c) 2017 Thomas Karl Pietrowski

# Build-ins
import os
import winreg

# Uranium/Cura
from UM.i18n import i18nCatalog
from UM.Message import Message
from UM.Logger import Logger
from UM.PluginRegistry import PluginRegistry

# Our plugin
from .CommonComReader import CommonCOMReader
from .SystemUtils import convertDosPathIntoLongPath

i18n_catalog = i18nCatalog("CuraDassaultSystemesPlugins")

def is_any_cat_installed():
    cat_app_name =  "CATIA.Application"
    try:
        # Could find a better key to detect whether SolidWorks is installed..
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, cat_app_name, 0, winreg.KEY_READ)
        return True
    except:
        return False

class CatiaReader(CommonCOMReader):
    def __init__(self):
        super().__init__("CATIA.Application", "Catia")

        self._extension_part = ".CATpart"
        self._supported_extensions = [self._extension_part.lower(),
                                      ]

        self.root_component = None
    
    @property
    def _file_formats_first_choice(self):
        _file_formats_first_choice = [] # Ordered list of preferred formats

        if PluginRegistry.getInstance().isActivePlugin("STLReader"):
            _file_formats_first_choice.append('stl')

        return _file_formats_first_choice

    def startApp(self, options):
        options = super().startApp(options)
        options["app_instance"].DisplayFileAlerts = False
        return options
    
    def setAppVisible(self, state, options):
        options["app_instance"].Visible = state

    def getAppVisible(self, state, options):
        return options["app_instance"].Visible

    def checkApp(self, options):
        functions_to_be_checked = ("Documents", "ActiveDocument")
        for func in functions_to_be_checked:
            try:
                getattr(options["app_instance"], func)
            except:
                Logger.logException("e", "Error which occurred when checking for a valid app instance")
                return False
        return True

    def closeApp(self, options):
        if "app_instance" in options.keys():
            options["app_instance"].DisplayFileAlerts = False
            options["app_instance"].Quit()

    def openForeignFile(self, options):
        options["cat_document"] = options["app_instance"].Documents.Open(options["foreignFile"])
        return options

    def exportFileAs(self, options):
        options["cat_document"].ExportData(options["tempFile"], options["tempType"])

    def closeForeignFile(self, options):
        if "app_instance" in options.keys():
            options["app_instance"].Documents.Item(os.path.split(options["foreignFile"])[1]).Close()
            #options["app_instance"].ActiveDocument.Close()
