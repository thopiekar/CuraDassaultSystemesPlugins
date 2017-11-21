# Copyright (c) 2017 Thomas Karl Pietrowski

from UM.Message import Message
from UM.Platform import Platform
from UM.i18n import i18nCatalog

i18n_catalog = i18nCatalog("SolidWorksPlugin")

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import SolidWorksReader
    from . import SolidWorksDialogHandler


def getMetaData():
    metaData = {"mesh_reader": [{
                                 "extension": "SLDPRT",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks part file")
                                },
                                {
                                 "extension": "SLDASM",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks assembly file")
                                },
                                {
                                 "extension": "SLDDRW",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks drawing file")
                                },
                               ]
                }
    
    return metaData

def register(app):
    # Solid works only runs on Windows.
    plugin_data = {}
    if Platform.isWindows():
        # TODO: Feature: Add at this point an early check, whether readers are available. See: reader.areReadersAvailable()
        reader = SolidWorksReader.SolidWorksReader()
        if reader.isOperational():
            plugin_data["mesh_reader"] = reader
        else:
            no_valid_installation_message = Message(i18n_catalog.i18nc("@info:status", "Dear customer,\nwe could not find a valid installation of SolidWorks on your system. That means, that either SolidWorks is not installed or you don't own an valid license. Please make sure that running SolidWorks itself works without issues and/or contact your ICT.\n\nWith kind regards\n - Thomas Karl Pietrowski"),
                                                    0)
            no_valid_installation_message.setTitle("SolidWorks plugin")
            no_valid_installation_message.show()
        
        plugin_data["extension"] = SolidWorksDialogHandler.SolidWorksDialogHandler()
    else:
        not_correct_os_message = Message(i18n_catalog.i18nc("@info:status", "Dear customer,\nyou are currently running this plugin on an operating system other than Windows. This plugin will only work on Windows with SolidWorks including an valid license. Please install this plugin on a Windows machine with SolidWorks installed.\n\nWith kind regards\n - Thomas Karl Pietrowski"),
                                                    0)
        not_correct_os_message.setTitle("SolidWorks plugin")
        not_correct_os_message.show()
    
    return plugin_data
