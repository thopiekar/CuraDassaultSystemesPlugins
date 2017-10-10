# Copyright (c) 2016 Thomas Karl Pietrowski

from UM.Platform import Platform

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("SolidWorksPlugin")

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import SolidWorksReader


def getMetaData():
    metaData = {"mesh_reader": [],
                }
    
    if SolidWorksReader.is_any_sldwks_installed():
        metaData["mesh_reader"] += [{
                                        "extension": "SLDPRT",
                                        "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks part file")
                                    },
                                    {
                                        "extension": "SLDASM",
                                        "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks assembly file")
                                    },
                                    ]
    
    return metaData

def register(app):
    # Solid works only runs on Windows.
    plugin_data = {}
    if Platform.isWindows():
        reader = SolidWorksReader.SolidWorksReader()
        # TODO: Feature: Add at this point an early check, whether readers are available. See: reader.areReadersAvailable()
        if SolidWorksReader.is_any_sldwks_installed():
            plugin_data["mesh_reader"] = reader
        from .SolidWorksDialogHandler import SolidWorksDialogHandler
        plugin_data["extension"] = SolidWorksDialogHandler()
    return plugin_data
