# Copyright (c) 2017 Thomas Karl Pietrowski

# built-ins
import os

# Uranium
from UM.Message import Message # @UnresolvedImport
from UM.Platform import Platform # @UnresolvedImport
from UM.i18n import i18nCatalog # @UnresolvedImport

i18n_catalog = i18nCatalog("SolidWorksPlugin")

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import SolidWorksReader # @UnresolvedImport
    from . import SolidWorksDialogHandler # @UnresolvedImport

def getMetaData():
    metaData = {"mesh_reader": [{
                                 "extension": "SLDPRT",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "3DS SolidWorks part file")
                                },
                                {
                                 "extension": "SLDASM",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "3DS SolidWorks assembly file")
                                },
                                {
                                 "extension": "SLDDRW",
                                 "description": i18n_catalog.i18nc("@item:inlistbox", "3DS SolidWorks drawing file")
                                },
                               ]
                }

    return metaData

def register(app):
    plugin_data = {}
    if Platform.isWindows():
        reader = SolidWorksReader.SolidWorksReader()
        if reader.isOperational():
            plugin_data["mesh_reader"] = reader
        else:
            no_valid_installation_message = Message(i18n_catalog.i18nc("@info:status",
                                                                       "Dear customer,\nWe could not find a valid installation of 3DS SolidWorks on your system. That means that either 3DS SolidWorks is not installed or you don't own an valid license. Please make sure that running 3DS SolidWorks itself works without issues and/or contact your ICT.\n\nWith kind regards\n - Thomas Karl Pietrowski"
                                                                       ),
                                                    0)
            no_valid_installation_message.setTitle("SolidWorks plugin")
            no_valid_installation_message.show()

        plugin_data["extension"] = SolidWorksDialogHandler.SolidWorksDialogHandler(reader)
    else:
        not_correct_os_message = Message(i18n_catalog.i18nc("@info:status",
                                                            "Dear customer,\nYou are currently running this plugin on an operating system other than Windows. This plugin will only work on Windows with 3DS SolidWorks installed, including an valid license. Please install this plugin on a Windows machine with 3DS SolidWorks installed.\n\nWith kind regards\n - Thomas Karl Pietrowski"
                                                            ),
                                         0)
        not_correct_os_message.setTitle("SolidWorks plugin")
        not_correct_os_message.show()

    return plugin_data
