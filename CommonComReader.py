# Copyright (c) 2017 Thomas Karl Pietrowski

# Buildins
import os
import tempfile
import threading
import uuid

# Uranium/Cura
from UM.Application import Application
from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("CuraSolidWorksIntegrationPlugin")
from UM.Message import Message
from UM.Logger import Logger
from UM.Mesh.MeshReader import MeshReader
from UM.PluginRegistry import PluginRegistry
from UM.Scene.SceneNode import SceneNode

# Trying to import one of the COM modules
try:
    import win32com.client
    import win32com.client.gencache
    import pythoncom
    import pywintypes

    class ComFactory:
        def CreateClassObject(app_name):
            return win32com.client.Dispatch(app_name)

        def Coinit():
            pythoncom.CoInitializeEx(pythoncom.COINIT_MULTITHREADED)

        def UnCoinit():
            pythoncom.CoUninitialize()

    Logger.log("i", "ComFactory: Using pywintypes!")

except ImportError:
    ## ComTypes
    import comtypes
    import comtypes.client

    class ComFactory:
        def CreateClassObject(app_name):
            return comtypes.client.GetClassObject(app_name).CreateInstance()

        def CoInit():
            comtypes.CoInitializeEx(comtypes.COINIT_MULTITHREADED)

        def UnCoInit():
            comtypes.CoUninitialize()

    Logger.log("i", "ComFactory: Using comtypes!")

class CommonCOMReader(MeshReader):
    conversion_lock = threading.Lock()

    def __init__(self, app_name, app_friendly_name):
        super().__init__()
        self._app_name = app_name
        self._app_friendly_name = app_friendly_name
        #self._file_formats_first_choice = []

        # Start/stop behaviour

        # Technically neither preloading nor keeping the instance up, is possible, since Cura calls the file reader from different/new threads
        # The error when trying to use it here is:
        # > pywintypes.com_error: (-2147417842, 'The application called an interface that was marshalled for a different thread.', None, None)
        self._app_preload = False
        self._app_keep_running = False

        """
        if self._app_preload and not self._app_keep_running:
            self._app_keep_running = True
        """

        # Preparations
        """
        if self._app_preload:
            Logger.log("d", "Preloading %s..." %(self._app_friendlyName))
            self.startApp()
        """

        #Logger.log("d", "Looking for readers...")
        #self.__init_builtin_readers__()

    #def __init_builtin_readers__(self):
    #    self._file_formats_first_choice = [] # Ordered list of preferred formats
    #    self._reader_for_file_format = {}
    #
    #    # Trying 3MF first because it describes the model much better..
    #    # However, this is untested since this plugin was only tested with STL support
    #    if PluginRegistry.getInstance().isActivePlugin("3MFReader"):
    #        self._reader_for_file_format["3mf"] = PluginRegistry.getInstance().getPluginObject("3MFReader")
    #        self._file_formats_first_choice.append("3mf")
    #
    #    if PluginRegistry.getInstance().isActivePlugin("STLReader"):
    #        self._reader_for_file_format["stl"] = PluginRegistry.getInstance().getPluginObject("STLReader")
    #        self._file_formats_first_choice.append("stl")
    #
    #    if not len(self._reader_for_file_format):
    #        Logger.log("d", "Could not find any reader for (probably) supported file formats!")

    @property
    def _reader_for_file_format(self):
        _reader_for_file_format = {}

        # Trying 3MF first because it describes the model much better..
        # However, this is untested since this plugin was only tested with STL support
        if PluginRegistry.getInstance().isActivePlugin("3MFReader"):
            _reader_for_file_format["3mf"] = PluginRegistry.getInstance().getPluginObject("3MFReader")

        if PluginRegistry.getInstance().isActivePlugin("STLReader"):
            _reader_for_file_format["stl"] = PluginRegistry.getInstance().getPluginObject("STLReader")

        if not len(_reader_for_file_format):
            Logger.log("d", "Could not find any reader for (probably) supported file formats!")

        return _reader_for_file_format

    def startApp(self, options):
        Logger.log("d", "Starting %s...", self._app_friendly_name)
        options["app_instance"] = ComFactory.CreateClassObject(self._app_name)

        return options

    def checkApp(self):
        raise NotImplementedError("Checking app is not implemented!")

    def getAppVisible(self, state):
        raise NotImplementedError("Toggle for visibility not implemented!")

    def setAppVisible(self, state, options):
        raise NotImplementedError("Toggle for visibility not implemented!")

    def closeApp(self, options):
        raise NotImplementedError("Procedure how to close your app is not implemented!")

    def openForeignFile(self, options):
        "This function shall return options again. It optionally contains other data, which is needed by the reader for other tasks later."
        raise NotImplementedError("Opening files is not implemented!")

    def exportFileAs(self, model, options):
        raise NotImplementedError("Exporting files is not implemented!")

    def closeForeignFile(self, options):
        raise NotImplementedError("Closing files is not implemented!")

    def nodePostProcessing(self, node):
        return node

    def read(self, file_path):
        try:
            # Let's convert only one file at a time!
            self.conversion_lock.acquire()

            return self._read(file_path)
        finally:
            self.conversion_lock.release()

    def _read(self, file_path):
        options = {"foreignFile": file_path,
                   "foreignFormat": os.path.splitext(file_path)[1],
                   }

        # Starting app and Coinit before
        ComFactory.Coinit()
        try:
            self.startApp(options)
        except Exception:
            Logger.logException("e", "Failed to start <%s>...", self._app_name)
            error_message = Message(i18n_catalog.i18nc("@info:status", "Error while starting {}!".format(self._app_friendly_name)))
            error_message.show()
            return None

        # Tell the 3rd party application to open a file...
        Logger.log("d", "Opening file with {}...".format(self._app_friendly_name))
        options = self.openForeignFile(options)

        # Append all formats which are not preferred to the end of the list
        fileFormats = self._file_formats_first_choice
        for file_format in self._reader_for_file_format.keys():
            if file_format not in fileFormats:
                fileFormats.append(file_format)

        # Trying to convert into all formats 1 by 1 and continue with the successful export
        Logger.log("i", "Trying to convert into: %s", fileFormats)
        scene_node = None
        for file_format in fileFormats:
            Logger.log("d", "Trying to convert <%s> into '%s'", file_path, file_format)

            options["tempType"] = file_format

            # Creating a unique file in the temporary directory..
            options["tempFile"] = os.path.join(tempfile.tempdir,
                                               "{}.{}".format(uuid.uuid4(), file_format.upper()),
                                               )

            Logger.log("d", "Using temporary file <%s>", options["tempFile"])

            # In case there is already a file with this name (very unlikely...)
            if os.path.isfile(options["tempFile"]):
                Logger.log("w", "Removing already available file, called: %s", options["tempFile"])
                os.remove(options["tempFile"])

            Logger.log("d", "Saving as: <%s>", options["tempFile"])
            try:
                self.exportFileAs(options)
            except:
                Logger.logException("e", "Could not export <%s> into '%s'.", file_path, file_format)
                continue

            if os.path.isfile(options["tempFile"]):
                Logger.log("d", "Saved as: <%s>", options["tempFile"])
            else:
                Logger.log("d", "Temporary file not found after export!")
                continue

            # Opening the resulting file in Cura
            try:
                reader = Application.getInstance().getMeshFileHandler().getReaderForFile(options["tempFile"])
                if not reader:
                    Logger.log("d", "Found no reader for %s. That's strange...", file_format)
                    continue
                Logger.log("d", "Using reader: %s", reader.getPluginId())
                scene_node = reader.read(options["tempFile"])
            except:
                Logger.logException("e", "Failed to open exported <%s> file in Cura!", file_format)
                continue

            # Remove the temp_file again
            Logger.log("d", "Removing temporary %s file, called <%s>", file_format, options["tempFile"])

            break

        # Closing document in the app
        self.closeForeignFile(options)

        # Closing the app again..
        self.closeApp(options)

        ComFactory.Coinit()

        # Nuke the instance!
        if "app_instance" in options.keys():
            del options["app_instance"]

        # the returned node from STL or 3MF reader can be a node or a list of nodes
        scene_node_list = scene_node
        if not isinstance(scene_node, list):
            scene_node_list = [scene_node]

        for node in scene_node_list:
            self.nodePostProcessing(node)

        return scene_node
