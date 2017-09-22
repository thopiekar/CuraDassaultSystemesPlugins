# Copyright (c) 2017 Ultimaker B.V.
# PluginBrowser is released under the terms of the AGPLv3 or higher.
from UM.Extension import Extension
from UM.i18n import i18nCatalog
from UM.Logger import Logger
from UM.PluginRegistry import PluginRegistry
from UM.Application import Application

from PyQt5.QtCore import QUrl, QObject, pyqtSlot
from PyQt5.QtQml import QQmlComponent, QQmlContext

import os

i18n_catalog = i18nCatalog("cura")


class DialogHandler(QObject, Extension):
    def __init__(self, parent = None):
        super().__init__(parent)
        self._config_dialog = None
        self._tutorial_dialog = None
        self.addMenuItem(i18n_catalog.i18n("Configure"), self._openConfigDialog)
        self.addMenuItem(i18n_catalog.i18n("How to install Cura SolidWorks macro"), self._openTutorialDialog)

    def _openConfigDialog(self):
        if not self._config_dialog:
            self._config_dialog = self._createDialog("ConfigDialog.qml")
        self._config_dialog.show()

    def _openTutorialDialog(self):
        if not self._tutorial_dialog:
            self._tutorial_dialog = self._createDialog("MacroTutorialDialog.qml")
        self._tutorial_dialog.show()

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

    @pyqtSlot()
    def openMacroAndIconDirectory(self):
        plugin_dir = os.path.join(PluginRegistry.getInstance().getPluginPath(self.getPluginId()))
        macro_dir = os.path.join(plugin_dir, "macro")
        os.system("explorer.exe \"%s\"" % macro_dir)
