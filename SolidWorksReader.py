# Copyright (c) 2017 Thomas Karl Pietrowski

# TODOs:
# * Adding selection to separately import parts from an assembly

# Build-ins
import math
import os
import winreg

# Uranium/Cura
from UM.i18n import i18nCatalog
from UM.Message import Message
from UM.Logger import Logger
from UM.Math.Vector import Vector
from UM.Math.Quaternion import Quaternion
from UM.Mesh.MeshReader import MeshReader
from UM.PluginRegistry import PluginRegistry

# Our plugin
from .CommonComReader import CommonCOMReader
from .SolidWorksConstants import SolidWorksEnums, SolidWorkVersions
from .SolidWorksReaderUI import SolidWorksReaderUI
from .SystemUtils import convertDosPathIntoLongPath
from .ComFactory import ComConnector


i18n_catalog = i18nCatalog("CuraDassaultSystemesPlugins")

def is_sldwks_service(major_version):
    sldwks_app_name =  "SldWorks.Application.{}".format(major_version)
    try:
        # Could find a better key to detect whether SolidWorks is installed..
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, sldwks_app_name, 0, winreg.KEY_READ)
        return True
    except:
        return False

def get_software_install_path(major_version):
    regpath = "SldWorks.Application.{}\shell\open\command".format(major_version)
    sldwks_exe = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, regpath)
    sldwks_exe = sldwks_exe.split()[0]
    sldwks_exe = convertDosPathIntoLongPath(sldwks_exe)
    
    sldwkd_inst = os.path.split(sldwks_exe)[0]
    return sldwkd_inst

def is_software_install_path(major_version):
    # Also check whether the executable can be found..
    # Why? - SolidWorks 2017 lefts an key after uninstallation, which points to an orphaned path.
    try:
        get_software_install_path(major_version)
        return True
    except:
        return False

def is_sldwks_installed(major_version):
    return is_sldwks_service(major_version) and is_software_install_path(major_version)
    
def return_available_versions():
    versions = []
    for major_version in SolidWorkVersions.major_version_name.keys(): # If one of "SldWorks.Application.*" exists, we also have a "SldWorks.Application"
        if is_sldwks_installed(major_version):
            versions.append(major_version)
    return versions

def is_any_sldwks_installed():
    return bool(return_available_versions())

class SolidWorksReader(CommonCOMReader):
    def __init__(self):
        super().__init__("SldWorks.Application", "SolidWorks")

        self._extension_part = ".SLDPRT"
        self._extension_assembly = ".SLDASM"
        self._supported_extensions = [self._extension_part.lower(),
                                      self._extension_assembly.lower(),
                                      ]

        self._convert_assembly_into_once = True  # False is not implemented now!
        self._revision = None
        self._revision_major = 0
        self._revision_minor = 0
        self._revision_patch = 0

        self._ui = SolidWorksReaderUI()
        self._selected_quality = None
        self._quality_value_map = {"coarse": SolidWorksEnums.swSTLQuality_e.swSTLQuality_Coarse,
                                   "fine": SolidWorksEnums.swSTLQuality_e.swSTLQuality_Fine}

        self.root_component = None


    @property
    def _app_names(self):
        return ["SldWorks.Application.{}".format(major_version) for major_version in return_available_versions()] + super()._app_names
    
    @property
    def _file_formats_first_choice(self):
        _file_formats_first_choice = [] # Ordered list of preferred formats

        # Trying 3MF first because it describes the model much better..
        # However, this is untested since this plugin was only tested with STL support
        if self._revision_major >= 25 and PluginRegistry.getInstance().isActivePlugin("3MFReader"):
            _file_formats_first_choice.append("3mf")

        if PluginRegistry.getInstance().isActivePlugin("STLReader"):
            _file_formats_first_choice.append("stl")

        return _file_formats_first_choice

    def preRead(self, file_name, *args, **kwargs):
        self._ui.showConfigUI()
        self._ui.waitForUIToClose()

        if self._ui.getCancelled():
            return MeshReader.PreReadResult.cancelled

        # get quality
        self._selected_quality = self._ui.quality
        if self._selected_quality is None:
            self._selected_quality = "fine"
        self._selected_quality = self._selected_quality.lower()

        # give actual value for quality
        self._selected_quality = self._quality_value_map.get(self._selected_quality,
                                                             SolidWorksEnums.swSTLQuality_e.swSTLQuality_Fine)

        return MeshReader.PreReadResult.accepted

    def setAppVisible(self, state, options):
        options["app_instance"].Visible = state

    def getAppVisible(self, state, options):
        return options["app_instance"].Visible

    def startApp(self, options):
        options = super().startApp(options)

        # Allow SolidWorks to run in the background and be invisible
        options["app_instance"].UserControl = False

        #  ' If the following property is true, then the SolidWorks frame will be visible on a call to ISldWorks::ActivateDoc2; so set it to false
        options["app_instance"].Visible = False

        # Keep SolidWorks frame invisible when ISldWorks::ActivateDoc2 is called
        options["app_frame"] = options["app_instance"].Frame
        options["app_frame"].KeepInvisible = True

        # Getting revision after starting
        revision_number = options["app_instance"].RevisionNumber
        self._revision = [int(x) for x in revision_number.split(".")]

        try:
            self._revision_major = self._revision[0]
            self._revision_minor = self._revision[1]
            self._revision_patch = self._revision[2]
        except IndexError:
            pass

        try:
            Logger.log("d", "Started %s", SolidWorkVersions.major_version_name[self._revision_major])
        except KeyError:
            Logger.logException("w", "Unable to get revision number from solid works RevisionNumber.")

        return options

    def checkApp(self, options):
        functions_to_be_checked = ("OpenDoc", "CloseDoc")
        for func in functions_to_be_checked:
            try:
                getattr(options["app_instance"], func)
            except:
                Logger.logException("e", "Error which occurred when checking for a valid app instance")
                return False
        return True

    def closeApp(self, options):
        if "app_frame" in options.keys():
            # Normally, we want to do that, but this confuses SolidWorks more than needed, it seems.
            #options["app_frame"].KeepInvisible = False
            pass
        if "app_instance" in options.keys():
            # Same here. By logic I would assume that we need to undo it, but when processing multiple parts, SolidWorks gets confused again..
            # Or there is another sense..
            #options["app_instance"].Visible = True

            # TODO: Check whether this can be useful. I assume it will close all documents from all windows.
            #options["app_instance"].CloseAllDocuments(True) # Ensures that all docs have been closed!
            pass

    def walkComponentsInAssembly(self, root = None):
        if root is None:
            root = self.root_component

        children = root.GetChildren

        if children:
            children = [self.walkComponentsInAssembly(child) for child in children]
            return root, children
        else:
            return root

        """
        models = options["sw_model"].GetComponents(True)

        for model in models:
            #Logger.log("d", model.GetModelDoc2())
            #Logger.log("d", repr(model.GetTitle))
            Logger.log("d", repr(model.GetPathName))
            #Logger.log("d", repr(model.GetType))
            if model.GetPathName in ComponentsCount.keys():
                ComponentsCount[model.GetPathName] = ComponentsCount[model.GetPathName] + 1
            else:
                ComponentsCount[model.GetPathName] = 1

        for key in ComponentsCount.keys():
            Logger.log("d", "Found %s %s-times in the assembly!" %(key, ComponentsCount[key]))
        """

    def openForeignFile(self, options):
        if options["foreignFormat"].upper() == self._extension_part:
            filetype = SolidWorksEnums.FileTypes.SWpart
        elif options["foreignFormat"].upper() == self._extension_assembly:
            filetype = SolidWorksEnums.FileTypes.SWassembly
        else:
            raise NotImplementedError("Unknown extension. Something went terribly wrong!")

        documentSpecification = options["app_instance"].GetOpenDocSpec(options["foreignFile"])
        filename = os.path.split(options["foreignFile"])[1]

        ## NOTE: SPEC: FileName
        #documentSpecification.FileName

        ## NOTE: SPEC: DocumentType
        ## TODO: Really needed here?!
        documentSpecification.DocumentType = filetype

        ## TODO: Test the impact of LightWeight = True
        #documentSpecification.LightWeight = True
        documentSpecification.Silent = True

        ## TODO: Double check, whether file was really opened read-only..
        documentSpecification.ReadOnly = True

        documentSpecificationObject = ComConnector.GetComObject(documentSpecification)
        options["sw_model"] = options["app_instance"].OpenDoc7(documentSpecificationObject)

        if documentSpecification.Warning:
            Logger.log("w", "Warnings happened while opening your SolidWorks file!")
        if documentSpecification.Error:
            Logger.log("e", "Errors happened while opening your SolidWorks file!")
            error_message = Message(i18n_catalog.i18nc("@info:status", "Errors appeared while opening your SolidWorks file! \
            Please check, whether it is possible to open your file in SolidWorks itself without any problems as well!" ))
            error_message.show()

        try:
            error, model_pointer = options["app_instance"].ActivateDoc3(filename, True, SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc)
            if model_pointer is None:
                raise ValueError("No pointer has been returned by ActivateDoc3. Something went totally wrong!")
            Logger.log("i", "Active document is now: <%s>", options["app_instance"].IActiveDoc2.GetPathName())
        except:
            Logger.log("d", "Activating the document failed. A patch in comtypes is needed to fix that!")

        # Might be useful in the future, but no need for this ATM
        #self.configuration = self.model.getActiveConfiguration
        #self.root_component = self.configuration.GetRootComponent

        ## EXPERIMENTAL: Browse single parts in assembly
        #if filetype == SolidWorksEnums.FileTypes.SWassembly:
        #    Logger.log("d", 'walkComponentsInAssembly: ' + repr(self.walkComponentsInAssembly()))

        return options

    def exportFileAs(self, options):
        if options["tempType"] == "stl":
            if options["foreignFormat"].upper() == self._extension_assembly:
                # Backing up current setting of swSTLComponentsIntoOneFile
                swSTLComponentsIntoOneFileBackup = options["app_instance"].GetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile)
                options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile, self._convert_assembly_into_once)

            swExportSTLQualityBackup = options["app_instance"].GetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality)
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality, SolidWorksEnums.swSTLQuality_e.swSTLQuality_Fine)

            # Changing the default unit for STLs to mm, which is expected by Cura
            swExportStlUnitsBackup = options["app_instance"].GetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits)
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits, SolidWorksEnums.swLengthUnit_e.swMM)

            # Changing the output type temporary to binary
            swSTLBinaryFormatBackup = options["app_instance"].GetUserPreferenceToggle(SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat)
            options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat, True)

        options["sw_model"].SaveAs(options["tempFile"])

        if options["tempType"] == "stl":
            # Restoring swSTLBinaryFormat
            options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat, swSTLBinaryFormatBackup)

            # Restoring swExportStlUnits
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits, swExportStlUnitsBackup)

            # Restoring swSTLQuality_Fine
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality, swExportSTLQualityBackup)

            if options["foreignFormat"].upper() == self._extension_assembly:
                # Restoring swSTLComponentsIntoOneFile
                options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile, swSTLComponentsIntoOneFileBackup)

    def closeForeignFile(self, options):
        if "app_instance" in options.keys():
            #options["app_instance"].CloseDoc(options["foreignFile"])
            options["app_instance"].QuitDoc(options["foreignFile"])

    ## TODO: A functionality like this needs to come back as soon as we have something like a dependency resolver for plugins.
    #def areReadersAvailable(self):
    #    return bool(self._reader_for_file_format)

    def nodePostProcessing(self, nodes):
        # TODO: Investigate how the status is on SolidWorks 2018 (now beta)
        if self._revision_major >= 24: # Known problem under SolidWorks 2016 until 2017: Exported models are rotated by -90 degrees. This rotates it back!
            for node in nodes:
                rotation = Quaternion.fromAngleAxis(math.radians(90), Vector.Unit_X)
                node.rotate(rotation)
        return nodes

    ## Decide if we need to use ascii or binary in order to read file
