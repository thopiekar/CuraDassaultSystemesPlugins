# Copyright (c) 2016 Thomas Karl Pietrowski

# TODO: Adding support for basic CATIA support

from UM.Platform import Platform

from UM.i18n import i18nCatalog
i18n_catalog = i18nCatalog("CuraSolidWorksIntegrationPlugin")

if Platform.isWindows():
    # For installation check
    import winreg
    # The reader plugin itself
    from . import SolidWorksReader


def getMetaData():
    return {
        "mesh_reader":
        [
            {
                "extension": "SLDPRT",
                "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks part file")
            },
            {
                "extension": "SLDASM",
                "description": i18n_catalog.i18nc("@item:inlistbox", "SolidWorks assembly file")
            }
        ]
    }

    # TODO:
    # Needs more documentation on how to convert a CATproduct in CATIA using COM API
    #
    #{
    #    "extension": "CATProduct",
    #    "description": i18n_catalog.i18nc("@item:inlistbox", "CATproduct file")
    #}


def register(app):
    # Solid works only runs on Windows.
    plugin_data = {}
    if Platform.isWindows():
        reader = SolidWorksReader.SolidWorksReader()
        # TODO: Feature: Add at this point an early check, whether readers are available. See: reader.areReadersAvailable()
        if SolidWorksReader.is_software_available():
            plugin_data["mesh_reader"] = reader
        from .ConfigDialog import ConfigDialog
        plugin_data["extension"] = ConfigDialog()
    return plugin_data
