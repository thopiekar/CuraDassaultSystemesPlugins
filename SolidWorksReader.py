# Copyright (c) 2017 Thomas Karl Pietrowski

# TODOs:
# * Adding selection to separately import parts from an assembly

# Build-ins
import math
import os
import winreg

# Uranium/Cura
from UM.i18n import i18nCatalog # @UnresolvedImport
from UM.Logger import Logger # @UnresolvedImport
from UM.Math.Matrix import Matrix # @UnresolvedImport
from UM.Math.Vector import Vector # @UnresolvedImport
from UM.Math.Quaternion import Quaternion # @UnresolvedImport
from UM.Mesh.MeshReader import MeshReader # @UnresolvedImport
from UM.Message import Message # @UnresolvedImport
from UM.PluginRegistry import PluginRegistry # @UnresolvedImport
from UM.Preferences import Preferences # @UnresolvedImport

# Our plugin
from .CadIntegrationUtils.CommonComReader import CommonCOMReader # @UnresolvedImport
from .CadIntegrationUtils.ComFactory import ComConnector # @UnresolvedImport
from .CadIntegrationUtils.SystemUtils import convertDosPathIntoLongPath # @UnresolvedImport
from .SolidWorksConstants import SolidWorksEnums, SolidWorkVersions # @UnresolvedImport
from .SolidWorksDialogHandler import SolidWorksReaderWizard # @UnresolvedImport

# 3rd-party
import numpy

i18n_catalog = i18nCatalog("SolidWorksPlugin")

DEBUG = False
EMULATE_VERSION_API = 25

class SolidWorksReader(CommonCOMReader):
    def __init__(self):
        super().__init__("SolidWorks", "SldWorks.Application")

        Preferences.getInstance().addPreference("cura_solidworks/preferred_installation", -1)
        Preferences.getInstance().addPreference("cura_solidworks/export_quality", 0)
        Preferences.getInstance().addPreference("cura_solidworks/show_export_settings_always", True)
        Preferences.getInstance().addPreference("cura_solidworks/auto_rotate", True)

        self._extension_part = ".SLDPRT"
        self._extension_assembly = ".SLDASM"
        self._extension_drawing = ".SLDDRW"
        self._supported_extensions = [self._extension_part.lower(),
                                      self._extension_assembly.lower(),
                                      self._extension_drawing.lower(),
                                      ]

        self._convert_assembly_into_once = True  # False is not implemented now!

        self._ui = SolidWorksReaderWizard(self)

        self.quality_classes = {
                                30 : "Fine (3D-printing)",
                                20 : "Coarse (3D-printing)",
                                10 : "Fine (SolidWorks)",
                                 0 : "Coarse (SolidWorks)",
                                }

        self.root_component = None
        
        # Results of the validation checks of each version
        self.operational_versions = []
        self.technical_infos_per_version = {}
        
        # Check for operational installations
        Preferences.getInstance().addPreference("cura_solidworks/checks_at_initialization", True)
        self.updateOperationalInstallations(skip_all_tests = not self.checksAtInitialization)

    @property
    def checksAtInitialization(self):
        return Preferences.getInstance().getValue("cura_solidworks/checks_at_initialization")

    @property
    def _app_names(self):
        return [self.getVersionedServiceName(version) for version in self.operational_versions] + super()._app_names
    
    @property
    def _prefered_app_name(self):
        installation_code = Preferences.getInstance().getValue("cura_solidworks/preferred_installation")
        if isinstance(installation_code, str):
            installation_code = eval(installation_code)
        if isinstance(installation_code, float):
            installation_code = int(installation_code)
        
        if installation_code is -1:
            return None # We have no preference
        elif installation_code is -2:
            return self._default_app_name # Use system default service
        elif installation_code in self.operational_versions:
            return self.getVersionedServiceName(installation_code) # Use chosen version
        return None
    
    def getVersionedServiceName(self, version):
        return "SldWorks.Application.{}".format(version)
    
    def getFriendlyName(self, revision_major):
        if revision_major in SolidWorkVersions.major_version_name.keys():
            return SolidWorkVersions.major_version_name[revision_major]
        else:
            Logger.log("d", "revision_major: {}".format(repr(revision_major)))
            return self.getVersionedServiceName(revision_major)
    
    def getServicesFromRegistry(self):
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
        versions.sort()
        versions.reverse()
        return versions
    
    def isServiceRegistered(self, major_version):
        sldwks_app_name = self.getVersionedServiceName(major_version)
        try:
            # Could find a better key to detect whether SolidWorks is installed..
            winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, sldwks_app_name, 0, winreg.KEY_READ)
            return True
        except:
            return False
    
    def getSoftwareInstallPath(self, major_version):
        executable_extension = ".exe"
        regpath = "{}\shell\open\command".format(self.getVersionedServiceName(major_version))
        sldwks_exe = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, regpath)
        sldwks_exe = sldwks_exe[:sldwks_exe.find(executable_extension)+len(executable_extension)+1]
        sldwks_exe = convertDosPathIntoLongPath(sldwks_exe)
        sldwkd_inst = os.path.split(sldwks_exe)[0]
        return sldwkd_inst
    
    def isSoftwareInstallPath(self, major_version):
        # Also check whether the executable can be found..
        # Why? - SolidWorks 2017 lefts an key after uninstallation, which points to an orphaned path.
        try:
            self.getSoftwareInstallPath(major_version)
            return True
        except:
            return False
    
    def isServiceStartingUp(self, version, keep_instance_running = False, options = {}):
        # Also shall confirm the correct major revision from the running instance
        if not options:
            options = {"app_name": self.getVersionedServiceName(version), 
                       }
        try:
            if "app_instance" not in options.keys():
                self.startApp(options)
        except:
            Logger.logException("e", "Starting the service and getting the major revision number failed!")
        
        if "app_instance" in options.keys():
            if not keep_instance_running:
                self.closeApp(options)
                if not options["app_was_active"] and not self.getOpenDocuments(options):
                    Logger.log("d", "Looks like we opened SolidWorks and there are no open files. Let's close SolidWorks again!")
                    options["app_instance"].ExitApp()
                self.postCloseApp(options)
        else:
            Logger.log("e", "Starting service failed!")
            return (False, options)
        
        return (True, options)
    
    def isServiceConfirmingMajorRevision(self, version, keep_instance_running = False, options = {}):
        # Also shall confirm the correct major revision from the running instance
        if not options:
            options = {"app_name": self.getVersionedServiceName(version), 
                       }
        revision = [-1,]
        try:
            if "app_instance" not in options.keys():
                self.startApp(options)
            revision = self.getRevisionNumber(options)
        except:
            Logger.logException("e", "Starting the service and getting the major revision number failed!")
        
        if "app_instance" in options.keys():
            if not keep_instance_running:
                self.closeApp(options)
                if not options["app_was_active"] and not self.getOpenDocuments(options):
                    Logger.log("d", "Looks like we opened SolidWorks and there are no open files. Let's close SolidWorks again!")
                    # SolidWorks API: ?
                    options["app_instance"].ExitApp()
                self.postCloseApp(options)
        else:
            Logger.log("e", "Starting service failed!")
            return (False, options)
        
        if revision[0] == version:
            return (True, options)
        
        Logger.log("e", "Revision does not fit to {}.x.y: {}".format(version, revision[0]))
        return (False, options)
    
    def checkForBasicFunctions(self, version, keep_instance_running = False, options = {}):
        functions_to_be_checked = ("OpenDoc7",
                                   "CloseDoc",
                                   )
        
        # Also shall confirm the correct major revision from the running instance
        if not options:
            options = {"app_name": self.getVersionedServiceName(version), 
                       }
        functions_found = True
        try:
            if "app_instance" not in options.keys():
                self.startApp(options)
            for func in functions_to_be_checked:
                try:
                    getattr(options["app_instance"], func)
                except:
                    Logger.logException("e", "Error which occurred when checking for some functions")
                    functions_found = False
        except:
            Logger.logException("e", "Starting the service and checking for some functions failed!")
        
        if "app_instance" in options.keys():
            if not keep_instance_running:
                self.closeApp(options)
                if not options["app_was_active"] and not self.getOpenDocuments(options):
                    Logger.log("d", "Looks like we opened SolidWorks and there are no open files. Let's close SolidWorks again!")
                    # SolidWorks API: ?
                    options["app_instance"].ExitApp()
                self.postCloseApp(options)
        else:
            Logger.log("e", "Starting service failed!")
            return (False, options)
        
        if functions_found:
            return (True, options)
        else:
            Logger.log("e", "Could not find some functions!")
            return (False, options)

    def isVersionOperational(self, version):
        info_dict = {
                    "COM registered": False,
                    "Executable found": False,
                    "COM starting": False,
                    "Revision number": False,
                    "Functions available": False,
                    
                    }
        if DEBUG:
            if EMULATE_VERSION_API is version:
                Logger.log("d", "Passing all tests for API {}!".format(version))
                for key in info_dict.keys():
                    info_dict[key] = True
                return (True, info_dict)
        
        # Full set of checks for a working installation
        if not self.isServiceRegistered(version):
            Logger.log("w", "Found no COM service for '{}'! Ignoring..".format(self.getVersionedServiceName(version)))
            return (False, info_dict)
        info_dict["COM registered"] = True
        
        if not self.isSoftwareInstallPath(version):
            Logger.log("w", "Found no executable for '{}'! Ignoring..".format(self.getVersionedServiceName(version)))
            return (False, info_dict)
        info_dict["Executable found"] = True
        
        result, options = self.isServiceStartingUp(version, keep_instance_running = True)
        if not result:
            Logger.log("w", "Couldn't start COM server '{}'! Ignoring..".format(self.getVersionedServiceName(version)))
            return (False, info_dict)
        info_dict["COM starting"] = True
        
        result, options = self.isServiceConfirmingMajorRevision(version, keep_instance_running = True, options = options)
        if not result:
            Logger.log("w", "COM server can't confirm the major version for '{}'. This is a rotten installation! Ignoring..".format(self.getVersionedServiceName(version)))
            return (False, info_dict)
        info_dict["Revision number"] = True
        
        result, options = self.checkForBasicFunctions(version, options = options)
        if not result:
            Logger.log("w", "Can't find some basic functions to control '{}'! Ignoring..".format(self.getVersionedServiceName(version)))
            return (False, info_dict)
        info_dict["Functions available"] = True
        
        Logger.log("i", "Success! Installation of '{}' seems to be valid!".format(self.getVersionedServiceName(version)))
        return (True, info_dict)
    
    def updateOperationalInstallations(self, skip_all_tests = False):
        self.operational_versions = []
        self.technical_infos_per_version = {}
        versions = self.getServicesFromRegistry()
        if DEBUG:
            if EMULATE_VERSION_API not in self.operational_versions:
                versions.append(EMULATE_VERSION_API)
        for version in versions:
            if skip_all_tests or DEBUG:
                self.operational_versions.append(version)
                if DEBUG:
                    self.technical_infos_per_version[version] = self.isVersionOperational(version)[1]
                continue
            result, info = self.isVersionOperational(version)
            self.technical_infos_per_version[version] = info
            if result:
                self.operational_versions.append(version)
    
    def isOperational(self):
        # Whenever there are versions, which work, we are good to go!
        if self.operational_versions:
            return True
        return False

    def preRead(self, options):
        super().preRead(options)

        Logger.log("d", "Showing wizard, if needed..")
        self._ui.showConfigUI(blocking = True)
        if self._ui.getCancelled():
            Logger.log("d", "User cancelled conversion of file!")
            return MeshReader.PreReadResult.cancelled
        Logger.log("d", "Continuing to convert file..")

        return MeshReader.PreReadResult.accepted

    def setAppVisible(self, state, options):
        # SolidWorks API: ?
        options["app_instance"].Visible = state

    def getAppVisible(self, state, options):
        # SolidWorks API: ?
        return options["app_instance"].Visible

    def preStartApp(self, options):
        options["app_export_quality"] = Preferences.getInstance().getValue("cura_solidworks/export_quality")
        if options["app_export_quality"] is None:
            options["app_export_quality"] = 10 # Fine profile as default!
        if isinstance(options["app_export_quality"], str):
            options["app_export_quality"] = eval(options["app_export_quality"])
        if isinstance(options["app_export_quality"], float):
            options["app_export_quality"] = int(options["app_export_quality"])

        options["app_auto_rotate"] = Preferences.getInstance().getValue("cura_solidworks/auto_rotate")

    def getRevisionNumber(self, options):
        # Getting revision after starting
        if DEBUG:
            return [EMULATE_VERSION_API, 0, 0]
        
        # SolidWorks API: ?
        revision_number = options["app_instance"].RevisionNumber
        if isinstance(revision_number, str):
            revision_number = [int(x) for x in revision_number.split(".")]
            try:
                options["version_major"] = revision_number[0]
                Logger.log("d", "Major version is: {}".format(options["version_major"]))
                options["version_minor"] = revision_number[1]
                Logger.log("d", "Minor version is: {}".format(options["version_minor"]))
                options["version_patch"] = revision_number[2]
                Logger.log("d", "Patch version is: {}".format(options["version_patch"]))
            except IndexError:
                Logger.logException("w", "Unable to parse revision number from SolidWorks.RevisionNumber. revision_number is: {revision_number}.".format(revision_number = revision_number))
            except:
                Logger.logException("c", "Unexpected error: revision_number = {revision_number}".format(revision_number = revision_number))
        else:
            Logger.log("c", "revision_number has a wrong type: {}".format(type(revision_number)))
        
        return revision_number

    def startApp(self, options):
        if DEBUG:
            options["tempFileKeep"] = True
        else:
            super().startApp(options)
            
            # Tell SolidWorks we operating in the background
            # SolidWorks API: 2006 SP2 (Rev 14.2)
            options["app_operate_in_background"] = options["app_instance"].CommandInProgress # SolidWorks API: 2006 SP2 (Rev 14.2)
            options["app_instance"].CommandInProgress = True
            
            # Allow SolidWorks to run in the background and be invisible
            # SolidWorks API: ?
            options["app_instance_user_control"] = options["app_instance"].UserControl
            options["app_instance"].UserControl = False
            
            # If the following property is true, then the SolidWorks frame will be visible on a call to ISldWorks::ActivateDoc2; so set it to false
            # SolidWorks API: ?
            options["app_instance_visible"] = options["app_instance"].Visible
            options["app_instance"].Visible = False
            
            # Keep SolidWorks frame invisible when ISldWorks::ActivateDoc2 is called
            # SolidWorks API: ?
            options["app_frame"] = options["app_instance"].Frame
            options["app_frame_invisible"] = options["app_frame"].KeepInvisible
            options["app_frame"].KeepInvisible = True
        
        # Updating options["fileFormats"] depending on the started version
        revision = self.getRevisionNumber(options)
        options["fileFormats"] = [] # Ordered list of preferred formats
        
        # WORKAROUND: DISABLING 3MF-USAGE. THE READER RETURNS A NODE, WHICH FAILS TO BE ROTATED.
        #             WHEN DOING A SIMPLE ROATATION IT BLOWS UP THE MEMORY!
        # TODO: Adding check whether all readers are available per format!
        if revision[0] >= 25:
            options["fileFormats"].append("3mf")
        options["fileFormats"].append("stl")
        
        version_name = self.getFriendlyName(revision[0])
        Logger.log("d", "Started: %s", version_name)

        return options

    def closeApp(self, options):
        if "app_frame" in options.keys():
            # Normally, we want to do that, but this confuses SolidWorks more than needed, it seems.
            Logger.log("d", "Rolling back changes on app_frame.")
            if "app_frame_invisible" in options.keys():
                options["app_frame"].KeepInvisible = options["app_frame_invisible"]
            
        if "app_instance" in options.keys():
            # Same here. By logic I would assume that we need to undo it, but when processing multiple parts, SolidWorks gets confused again..
            # Or there is another sense..
            Logger.log("d", "Rolling back changes on app_instance.")
            if "app_instance_visible" in options.keys():
                # SolidWorks API: ?
                options["app_instance"].Visible = options["app_instance_visible"]
            if "app_instance_user_control" in options.keys():
                # SolidWorks API: ?
                options["app_instance"].UserControl = options["app_instance_user_control"]
            if "app_operate_in_background" in options.keys():
                # SolidWorks API: 2006 SP2 (Rev 14.2)
                options["app_instance"].CommandInProgress = options["app_operate_in_background"]
        Logger.log("d", "Closed SolidWorks.")

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

    def getOpenDocuments(self, options):
        open_files = []
        # SolidWorks API: 98Plus
        open_file = options["app_instance"].GetFirstDocument
        while open_file:
            open_files.append(open_file)
            open_file = open_file.GetNext
        Logger.log("i", "Found {} open files..".format(len(open_files)))
        return open_files

    def getOpenDocumentPaths(self, options):
        paths = []
        for document in self.getOpenDocuments(options):
            paths.append(document.GetPathName)
        return paths

    def getOpenDocumentFilepathDict(self, options):
        """
        Returns a dictionary of filepaths and document objects
        
        - Apparently we can't get .GetDocuments working
        """
        
        open_files = self.getOpenDocuments(options)
        open_file_paths = {}
        for open_file in open_files:
            open_file_paths[os.path.normpath(open_file.GetPathName)] = open_file
            open_file = open_file.GetNext
        return open_file_paths

    def getDocumentTitleByFilepath(self, options, filepath):
        open_files = self.getOpenDocumentFilepathDict(options)
        for open_file_path in open_files.keys():
            if os.path.normpath(filepath) == open_file_path:
                Logger.log("i", "Found title '{}' for file <{}>".format(open_files[open_file_path].GetTitle,
                                                                        open_file_path)
                           )
                return open_files[open_file_path].GetTitle
        return None

    def getDocumentsInDrawing(self, options):
        referenceModelNames = []
        # SolidWorks API: ?
        swView = options["sw_model"].GetFirstView
        while not swView is None:
            if swView.GetReferencedModelName not in referenceModelNames and swView.GetReferencedModelName != "":
                referenceModelNames.append(swView.GetReferencedModelName)
            swView = swView.GetNextView
        return referenceModelNames
    
    def countDocumentsInDrawing(self, options):
        return len(self.getDocumentsInDrawing(options))

    def activatePreviousFile(self, options):
        if "sw_previous_active_file" in options.keys():
            if options["sw_previous_active_file"] and "GetTitle" in dir(options["sw_previous_active_file"]):
                error = ComConnector.getByVarInt()
                # SolidWorks API: >= 20.0.x
                options["app_instance"].ActivateDoc3(options["sw_previous_active_file"].GetTitle,
                                                     True,
                                                     SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc,
                                                     error
                                                     )
        return options

    def openForeignFile(self, options):
        if DEBUG:
            return options
        open_file_paths = self.getOpenDocumentPaths(options)
        
        # SolidWorks API: X
        options["sw_previous_active_file"] = options["app_instance"].ActiveDoc
        # If the file has not been loaded open it!
        if not os.path.normpath(options["foreignFile"]) in open_file_paths:
            Logger.log("d", "Opening the foreign file!")
            if options["foreignFormat"].upper() == self._extension_part:
                filetype = SolidWorksEnums.swDocumentTypes_e.swDocPART
            elif options["foreignFormat"].upper() == self._extension_assembly:
                filetype = SolidWorksEnums.swDocumentTypes_e.swDocASSEMBLY
            elif options["foreignFormat"].upper() == self._extension_drawing:
                filetype = SolidWorksEnums.swDocumentTypes_e.swDocDRAWING
            else:
                raise NotImplementedError("Unknown extension. Something went terribly wrong!")
    
            # SolidWorks API: 2008 FCS (Rev 16.0)
            documentSpecification = options["app_instance"].GetOpenDocSpec(options["foreignFile"])
    
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
            # SolidWorks API: 2008 FCS (Rev 16.0)
            options["sw_model"] = options["app_instance"].OpenDoc7(documentSpecificationObject)

            if documentSpecification.Warning:
                Logger.log("w", "Warnings happened while opening your SolidWorks file!")
            if documentSpecification.Error:
                Logger.log("e", "Errors happened while opening your SolidWorks file!")
                error_message = Message(i18n_catalog.i18nc("@info:status", "SolidWorks reported errors while opening your file. We recommend to solve these issues inside SolidWorks itself."))
                error_message.setTitle("SolidWorks plugin")
                error_message.show()
            options["sw_opened_file"] = True
        else:
            Logger.log("d", "Foreign file has already been opened!")
            options["sw_model"] = self.getOpenDocumentFilepathDict(options)[os.path.normpath(options["foreignFile"])]
            options["sw_opened_file"] = False

        if options["foreignFormat"].upper() == self._extension_drawing:
            count_of_documents = self.countDocumentsInDrawing(options)
            if count_of_documents == 0:
                error_message = Message(i18n_catalog.i18nc("@info:status", "Found no models inside your drawing. Could you please check its content again and make sure one part or assembly is inside?\n\nThanks!"))
                error_message.setTitle("SolidWorks plugin")
                error_message.show()
            elif count_of_documents > 1:
                error_message = Message(i18n_catalog.i18nc("@info:status", "Found more than one part or assembly inside your drawing. We currently only support drawings with exactly one part or assembly inside.\n\nSorry!"))
                error_message.setTitle("SolidWorks plugin")
                error_message.show()
            else:
                options["sw_drawing"] = options["sw_model"]
                options["sw_drawing_opened"] = options["sw_opened_file"]
                options["foreignFile"] = self.getDocumentsInDrawing(options)[0]
                options["foreignFormat"] = os.path.splitext(options["foreignFile"])[1]
                self.activatePreviousFile(options)
                
                options = self.openForeignFile(options)

        error = ComConnector.getByVarInt()
        # SolidWorks API: >= 20.0.x
        # SolidWorks API: 2001Plus FCS (Rev. 10.0) - GetTitle
        options["app_instance"].ActivateDoc3(options["sw_model"].GetTitle,
                                             True,
                                             SolidWorksEnums.swRebuildOnActivation_e.swDontRebuildActiveDoc,
                                             error,
                                             )

        # Might be useful in the future, but no need for this ATM
        #self.configuration = options["sw_model"].getActiveConfiguration
        #self.root_component = self.configuration.GetRootComponent

        ## EXPERIMENTAL: Browse single parts in assembly
        #if filetype == SolidWorksEnums.FileTypes.SWassembly:
        #    Logger.log("d", 'walkComponentsInAssembly: ' + repr(self.walkComponentsInAssembly()))

        return options

    def exportFileAs(self, options, quality_enum = None):
        if DEBUG:
            _plugin_dir = os.path.split(__file__)[0]
            _test_file = os.path.join(_plugin_dir,
                                      "tests",
                                      "file_type_examples",
                                      "test_cube.{}".format(options["tempType"].lower())
                                      )
            if not os.path.isfile(_test_file):
                Logger.log("w", "Test file not found!")
            options["tempFile"] = _test_file
            Logger.log("w", "Overriding 'tempFile' with: {}".format(options["tempFile"]))
            return options
        
        if options["tempType"] == "stl":
            # # Backing up everything
            if options["foreignFormat"].upper() == self._extension_assembly:
                # Backing up current setting of swSTLComponentsIntoOneFile
                # SolidWorks API: 2009 FCS (Rev 17.0)
                swSTLComponentsIntoOneFileBackup = options["app_instance"].GetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile)
            
            # Backing up quality settings
            # SolidWorks API: ?
            swExportSTLQualityBackup = options["app_instance"].GetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality)
            swExportSTLAngleToleranceBackup = options["app_instance"].GetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance)
            swExportSTLDeviationBackup = options["app_instance"].GetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation)
            
            # Backing up the default unit for STLs to mm, which is expected by Cura
            # SolidWorks API: ?
            swExportStlUnitsBackup = options["app_instance"].GetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits)
            # Backing up the output type temporary to binary
            # SolidWorks API: 2009 FCS (Rev 17.0)
            swSTLBinaryFormatBackup = options["app_instance"].GetUserPreferenceToggle(SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat)
            
            # # Setting everything up
            # Export for assemblies
            if options["foreignFormat"].upper() == self._extension_assembly:
                # Setting up swSTLComponentsIntoOneFile
                # SolidWorks API: 2001 Plus FCS (Rev 10.0)
                options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile,
                                                                self._convert_assembly_into_once)
            
            # Setting  quality
            # -1 := Custom (not supported yet!)
            #  0 := Coarse (as defined by SolidWorks)
            # 10 := Fine (as defined by SolidWorks)
            # 20 := Coarse (3D printing profile)
            # 30 := Fine (3D printing profile)
            
            if quality_enum in range(0, 10) or quality_enum < 0:
                Logger.log("i", "Using SolidWorks' coarse quality!")
                # Give actual value for quality
                # SolidWorks API: ?
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                                                                      SolidWorksEnums.swSTLQuality_e.swSTLQuality_Coarse)
            elif quality_enum in range(10, 20):
                Logger.log("i", "Using SolidWorks' fine quality!")
                # Give actual value for quality
                # SolidWorks API: ?
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                                                                      SolidWorksEnums.swSTLQuality_e.swSTLQuality_Fine)
            elif quality_enum in range(20, 30):
                Logger.log("i", "Using coarse quality for 3D printing!")
                # Give actual value for quality
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                                                                      SolidWorksEnums.swSTLQuality_e.swSTLQuality_Custom)
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance,
                                                                      5.0)
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation,
                                                                      0.4)
            elif quality_enum >= 30:
                Logger.log("i", "Using fine quality for 3D printing!")
                # Give actual value for quality
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                                                                      SolidWorksEnums.swSTLQuality_e.swSTLQuality_Custom)
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance,
                                                                      1.0)
                options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation,
                                                                      0.1)
            else:
                Logger.log("e", "Invalid value for quality: {}".format(quality_enum))

            # Changing the default unit for STLs to mm, which is expected by Cura
            # SolidWorks API: ?
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits,
                                                                  SolidWorksEnums.swLengthUnit_e.swMM)

            # Changing the output type temporary to binary
            # SolidWorks API: 2001 Plus FCS (Rev 10.0)
            options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat, True)

        options["sw_model"].SaveAs(options["tempFile"])

        if options["tempType"] == "stl":
            # Restoring swSTLBinaryFormat
            # SolidWorks API: 2001 Plus FCS (Rev 10.0)
            options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.swUserPreferenceToggle_e.swSTLBinaryFormat,
                                                            swSTLBinaryFormatBackup)

            # Restoring swExportStlUnits
            # SolidWorks API: ?
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportStlUnits,
                                                                  swExportStlUnitsBackup)

            # Restoring swSTL*
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLAngleTolerance,
                                                                  swExportSTLAngleToleranceBackup)
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceDoubleValue_e.swSTLDeviation,
                                                                  swExportSTLDeviationBackup)
            # SolidWorks API: ?
            options["app_instance"].SetUserPreferenceIntegerValue(SolidWorksEnums.swUserPreferenceIntegerValue_e.swExportSTLQuality,
                                                                  swExportSTLQualityBackup)

            if options["foreignFormat"].upper() == self._extension_assembly:
                # Restoring swSTLComponentsIntoOneFile
                # SolidWorks API: 2001 Plus FCS (Rev 10.0)
                options["app_instance"].SetUserPreferenceToggle(SolidWorksEnums.UserPreferences.swSTLComponentsIntoOneFile, swSTLComponentsIntoOneFileBackup)
        
        return options

    def closeForeignFile(self, options):
        if "app_instance" in options.keys():
            if "sw_opened_file" in options.keys():
                if options["sw_opened_file"]:
                    # SolidWorks API: ?
                    # SolidWorks API: 2001Plus FCS (Rev. 10.0) - GetTitle
                    options["app_instance"].CloseDoc(options["sw_model"].GetTitle)
            if "sw_drawing_opened" in options.keys():
                if options["sw_drawing_opened"]:
                    # SolidWorks API: ?
                    options["app_instance"].CloseDoc(options["sw_drawing"].GetTitle)
            self.activatePreviousFile(options)

    def nodePostProcessing(self, options, scene_nodes, revision = None):
        Logger.log("d", "Doing postprocessing on: {}".format(repr(scene_nodes)))
        super().nodePostProcessing(options, scene_nodes)
        # # Auto-rotation
        if options["app_auto_rotate"]:
            if options["tempType"] == "stl":
                Logger.log("d", "Doing auto-rotation..")
                # Known problem under SolidWorks 2016 until 2018:
                # Exported models are rotated by -90 degrees. This rotates them back!
                rotation = Quaternion.fromAngleAxis(math.radians(90), Vector.Unit_X)
                zero_translation = Matrix(data=numpy.zeros(3, dtype = numpy.float64))
                for scene_node in scene_nodes:
                    if not scene_node.hasChildren():
                        scene_node.rotate(rotation)
                        mesh_data = scene_node.getMeshData()
                        transformation_matrix = scene_node.getLocalTransformation()
                        transformation_matrix.setTranslation(zero_translation)
                        scene_node.setMeshData(mesh_data.getTransformed(transformation_matrix))
                    else:
                        Logger.log("d", "Passing children: {}".format(repr(scene_node.getChildren())))
                        self.nodePostProcessing(options, scene_node.getChildren(), revision = revision)
                return scene_nodes
            elif options["tempType"] == "3mf":
                for scene_node in scene_nodes:
                    Logger.log("d", "node: {}".format(dir(scene_node)))
                    zero_translation = Matrix()
                    scene_node.setTransformation(zero_translation)
                return scene_nodes
        return scene_nodes