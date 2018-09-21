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
from PyQt5.QtCore import QUrl, QObject # @UnresolvedImport
from PyQt5.QtQml import QQmlComponent, QQmlContext # @UnresolvedImport

# i18n
i18n_catalog = i18nCatalog("SolidWorksPlugin")

class SolidWorksUiCommons():
    def _createDialog(self, dialog_qml, directory = None):
        if directory is None:
            directory = PluginRegistry.getInstance().getPluginPath(self.getPluginId())
        path = QUrl.fromLocalFile(os.path.join(directory, dialog_qml))
        component = QQmlComponent(Application.getInstance()._engine, path)

        # We need access to engine (although technically we can't)
        context = QQmlContext(Application.getInstance()._engine.rootContext())
        context.setContextProperty("manager", self)
        dialog = component.create(context)
        if dialog is None:
            Logger.log("e", "QQmlComponent status %s", component.status())
            Logger.log("e", "QQmlComponent errorString %s", component.errorString())
        return dialog, context, component

    @pyqtSlot(int, result = bool)
    def isVersionOperational(self, major_version):
        return major_version in self.reader.operational_versions

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
        self.addMenuItem(i18n_catalog.i18n("Configure"),
                         self._openConfigDialog)
        self.addMenuItem(i18n_catalog.i18n("Installation guide for SolidWorks macro"),
                         self._openTutorialDialog)

    def _openConfigDialog(self):
        if not self._config_dialog:
            self._config_dialog, self._config_context, self._config_component = self._createDialog("SolidWorksConfiguration.qml")
        self._config_dialog.show()

    def _openTutorialDialog(self):
        if not self._tutorial_dialog:
            self._tutorial_dialog, self._tutorial_context, self._tutorial_component = self._createDialog("SolidWorksMacroTutorial.qml")
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
        Logger.log("d", "Showing wizard {} needed.. (preference = {})".format(["is", "is not"][preference],
                                                                              repr(preference)))
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
            self._ui_view, self._ui_context, self._ui_component = self._createDialog("SolidWorksWizard.qml", directory = os.path.split(__file__)[0])
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
