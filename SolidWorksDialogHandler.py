# Copyright (c) 2017 Ultimaker B.V.
# Copyright (c) 2017 Thomas Karl Pietrowski

import os
import threading

# Uranium
from UM.i18n import i18nCatalog # @UnresolvedImport
from UM.Application import Application # @UnresolvedImport
from UM.Extension import Extension # @UnresolvedImport
#from UM.FlameProfiler import pyqtSlot # @UnresolvedImport
from UM.Logger import Logger # @UnresolvedImport
from UM.PluginRegistry import PluginRegistry # @UnresolvedImport
from UM.Preferences import Preferences # @UnresolvedImport

# PyQt5
from PyQt5.QtCore import pyqtSignal, pyqtSlot # @UnresolvedImport
from PyQt5.QtCore import Qt, QUrl, QObject # @UnresolvedImport
from PyQt5.QtQml import QQmlComponent, QQmlContext # @UnresolvedImport

# i18n
i18n_catalog = i18nCatalog("SolidWorksPlugin")

class SolidWorksUiCommons():
    def _createDialog(self, dialog_qml):
        path = QUrl.fromLocalFile(os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()), dialog_qml))
        self._qml_component = QQmlComponent(Application.getInstance()._engine, path)

        # We need access to engine (although technically we can't)
        self._qml_context = QQmlContext(Application.getInstance()._engine.rootContext())
        self._qml_context.setContextProperty("manager", self)
        dialog = self._qml_component.create(self._qml_context)
        if dialog is None:
            Logger.log("e", "QQmlComponent status %s", self._qml_component.status())
            Logger.log("e", "QQmlComponent errorString %s", self._qml_component.errorString())
        return dialog

    @pyqtSlot(int, str, result = bool)
    def getTechnicalInfoPerVersion(self, revision, name):
        return bool(self.reader.technical_infos_per_version[revision][name])

    @pyqtSlot(result = list)
    def getVersionsList(self):
        versions = list(self.reader.technical_infos_per_version.keys()) 
        versions.sort()
        versions.reverse()
        return versions
    
    @pyqtSlot(result = int)
    def getVersionsCount(self):
        return int(len(list(self.reader.technical_infos_per_version.keys())))
    
    @pyqtSlot(int, result = str)
    def getFriendlyName(self, major_revision):
        return self.reader.getFriendlyName(major_revision)

class SolidWorksDialogHandler(QObject, Extension, SolidWorksUiCommons):
    
    def __init__(self, reader, parent = None):
        super().__init__(parent)
        self.reader = reader
        self._config_dialog = None
        self._tutorial_dialog = None
        self.addMenuItem(i18n_catalog.i18n("Configure"), self._openConfigDialog)
        self.addMenuItem(i18n_catalog.i18n("Installation guide for SolidWorks macro"), self._openTutorialDialog)

    def _openConfigDialog(self):
        if not self._config_dialog:
            self._config_dialog = self._createDialog("SolidWorksConfiguration.qml")
        self._config_dialog.show()

    def _openTutorialDialog(self):
        if not self._tutorial_dialog:
            self._tutorial_dialog = self._createDialog("SolidWorksMacroTutorial.qml")
        self._tutorial_dialog.show()

    @pyqtSlot()
    def openMacroAndIconDirectory(self):
        plugin_dir = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()))
        macro_dir = os.path.join(plugin_dir, "macro")
        os.system("explorer.exe \"%s\"" % macro_dir)

class SolidWorksReaderWizard(QObject, SolidWorksUiCommons):
    show_config_ui_trigger = pyqtSignal()

    def __init__(self, reader):
        super().__init__()

        self.reader = reader

        Preferences.getInstance().addPreference("cura_solidworks/export_quality", 0)
        Preferences.getInstance().addPreference("cura_solidworks/show_export_settings_always", True)
        Preferences.getInstance().addPreference("cura_solidworks/auto_rotate", True)

        self._cancelled = False
        self._ui_view = None
        self.show_config_ui_trigger.connect(self._onShowConfigUI)

        self._ui_lock = threading.Lock()

    def getCancelled(self):
        return self._cancelled

    def waitForUIToClose(self):
        Logger.log("d", "Waitiung for UI to close..")
        self._ui_lock.acquire()
        Logger.log("d", "Got lock and releasing it now..")
        self._ui_lock.release()
        Logger.log("d", "Lock released!")

    def showConfigUI(self, blocking = False):
        self._ui_lock.acquire()
        preference = Preferences.getInstance().getValue("cura_solidworks/show_export_settings_always")
        Logger.log("d", "Showing wizard {} needed.. (preference = {})".format(["is", "is not"][preference], repr(preference)))
        if not preference:
            self._ui_lock.release()
            return
        self._cancelled = False
        self.show_config_ui_trigger.emit()
        
        if blocking:
            Logger.log("d", "Waiting for UI to close..")
            self.waitForUIToClose()

    def _onShowConfigUI(self):
        if self._ui_view is None:
            self._ui_view = self._createConfigUI("SolidWorksWizard.qml")
        self._ui_view.show()

    @pyqtSlot()
    def onOkButtonClicked(self):
        Logger.log("d", "Clicked on OkButton")
        self._cancelled = False
        self._ui_view.close()
        self._ui_lock.release()

    @pyqtSlot()
    def onCancelButtonClicked(self):
        Logger.log("d", "Clicked on CancelButton")
        self._cancelled = True
        self._ui_view.close()
        self._ui_lock.release()
