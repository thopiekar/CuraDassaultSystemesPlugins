# Copyright (c) 2016 Thomas Karl Pietrowski

from UM.Platform import Platform

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("CuraDassaultSystemesPlugins")

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import CatiaReader
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
    if CatiaReader.is_any_cat_installed():
        metaData["mesh_reader"] += [{
                                        "extension": "CATpart",
                                        "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks part file")
                                    },
                                    ]
    # TODO:
    # Needs more documentation on how to convert a CATproduct in CATIA using COM API
    #
    #{
    #    "extension": "CATProduct",
    #    "description": i18n_catalog.i18nc("@item:inlistbox", "CATproduct file")
    #}
    
    return metaData

def register(app):
    # Solid works only runs on Windows.
    plugin_data = {}
    if Platform.isWindows():
        # TODO: Feature: Add at this point an early check, whether readers are available. See: reader.areReadersAvailable()
        if SolidWorksReader.is_any_sldwks_installed():
            plugin_data["mesh_reader"] = SolidWorksReader.SolidWorksReader()
        if CatiaReader.is_any_cat_installed():
            plugin_data["mesh_reader"] = CatiaReader.CatiaReader()
        from .DialogHandler import DialogHandler
        plugin_data["extension"] = DialogHandler()
    return plugin_data
