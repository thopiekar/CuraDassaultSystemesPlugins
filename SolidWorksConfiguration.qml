// Copyright (c) 2017 Ultimaker B.V.
// Copyright (c) 2017 Thomas Karl Pietrowski

import QtQuick 2.1
import QtQuick.Controls 1.4
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.1 as UM

UM.Dialog
{
    width: Math.floor(screenScaleFactor * 365);
    minimumWidth: width;
    maximumWidth: width;

    height: Math.floor(screenScaleFactor * 250);
    minimumHeight: height;
    maximumHeight: height;

    title: catalog.i18nc("@title:window", "SolidWorks plugin: Configuration")

    onVisibilityChanged:
    {
        if (visible)
        {
            conversionTab.qualityDropdown.updateCurrentIndex();
            conversionTab.installations.updateCurrentIndex();
            conversionTab.showWizard.checked = UM.Preferences.getValue("cura_solidworks/show_export_settings_always");
            conversionTab.autoRotate.checked = UM.Preferences.getValue("cura_solidworks/auto_rotate");
        }
    }

    TabView {
        anchors.fill: parent
        UM.I18nCatalog{id: catalog; name: "SolidWorksPlugin"}

        Tab {
            title: catalog.i18nc("@title:tab", "Conversion settings");
            id: conversionTab
            
            property Item showWizard: item.showWizard
            property Item autoRotate: item.autoRotateCheckBox
            property Item qualityDropdown: item.qualityDropdown
            property Item qualityModel: item.choiceModel
            property Item installations: item.installationsDropdown
            
            GridLayout
            {
                Layout.fillWidth: true
                columnSpacing: 16 * screenScaleFactor
                rowSpacing: 10 * screenScaleFactor
                Layout.margins: 10 * screenScaleFactor
                columns: 1

                property Item showWizard: showWizardCheckBox
                property Item autoRotateCheckBox: autoRotateCheckBox
                property Item qualityDropdown: qualityDropdown
                property Item choiceModel: choiceModel
                property Item installationsDropdown: installationsDropdown

                Row {
                    width: parent.width

                    Label {
                        text: catalog.i18nc("@label", "First choice:");
                        width: 100 * screenScaleFactor
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    ComboBox
                    {
                        id: installationsDropdown
                        currentIndex: 0
                        width: 240 * screenScaleFactor

                        //style: UM.Theme.styles.combobox_color

                        function ensureListWithEntries()
                        {
                            var versions = manager.getVersionsList();
                            var version = 0;
                            var operational = true;
                            model.clear();
                            
                            model.append({ text: catalog.i18nc("@text:menu", "Latest installed version (Recommended)"), code: -1 });
                            for(var i = 0; i < versions.length; ++i)
                            {
                                version = versions[i];
                                operational = manager.isVersionOperational(version);
                                if (operational) {
                                    model.append({ text: manager.getFriendlyName(version), code: version });
                                }
                            }
                            model.append({ text: catalog.i18nc("@text:menu", "Default version"), code: -2 });
                            updateCurrentIndex()
                        }

                        function updateCurrentIndex()
                        {
                            var index = 0; // Top element in the list below by default
                            var currentSetting = UM.Preferences.getValue("cura_solidworks/preferred_installation");
                            for (var i = 0; i < model.count; ++i)
                            {
                                if (model.get(i).code == currentSetting)
                                {
                                    index = i;
                                    break;
                                }
                            }
                            currentIndex = index;
                        }

                        Component.onCompleted: {
                            ensureListWithEntries();
                        }

                        function saveInstallationCode()
                        {
                            var code = model.get(currentIndex).code;
                            UM.Preferences.setValue("cura_solidworks/preferred_installation", code);
                        }

                        model: ListModel
                        {
                            id: installationsModel
                            
                            Component.onCompleted:
                            {
                                append({ text: "NONE", code: -3 });
                            }
                        }
                    }
                }
                Row
                {
                    width: parent.width

                    Label {
                        text: catalog.i18nc("@action:label", "Quality:")
                        width: 100 * screenScaleFactor
                        anchors.verticalCenter: parent.verticalCenter
                    }

                    ComboBox
                    {
                        id: qualityDropdown

                        currentIndex: updateCurrentIndex()
                        width: 240 * screenScaleFactor

                        function updateCurrentIndex()
                        {
                            var index = 0; // Top element in the list below by default
                            var currentChoice = UM.Preferences.getValue("cura_solidworks/export_quality");
                            for (var i = 0; i < model.count; ++i)
                            {
                                if (model.get(i).code == currentChoice)
                                {
                                    index = i;
                                    break;
                                }
                            }
                            currentIndex = index;
                        }

                        function saveQualityCode()
                        {
                            var code = model.get(currentIndex).code;
                            UM.Preferences.setValue("cura_solidworks/export_quality", code);
                        }

                        model: ListModel
                        {
                            id: choiceModel

                            Component.onCompleted:
                            {
                                append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Fine (3D-printing)"), code: 30 });
                                append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Coarse (3D-printing)"), code: 20 });
                                append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Fine (SolidWorks)"), code: 10 });
                                append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Coarse (SolidWorks)"), code: 0 });
                            }
                        }
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: showWizardCheckBox
                        text: catalog.i18nc("@label", "Show wizard before opening SolidWorks files");
                        checked: UM.Preferences.getValue("cura_solidworks/show_export_settings_always");
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: autoRotateCheckBox
                        text: catalog.i18nc("@label", "Automatically rotate opened file into normed orientation");
                        checked: UM.Preferences.getValue("cura_solidworks/auto_rotate");
                    }
                }
            }
        }
        Tab {
            title: catalog.i18nc("@title:tab", "Installation(s)");
            id: installationsTab
            
            property Item versionDropdown: item.installationCheckDropdown
            
            GridLayout
            {
                Layout.fillWidth: true
                columnSpacing: 16 * screenScaleFactor
                rowSpacing: 10 * screenScaleFactor
                columns: 1

                property Item installationCheckDropdown: installationCheckDropdown

                Row {
                    width: parent.width

                    ComboBox
                    {
                        id: installationCheckDropdown
                        currentIndex: 0
                        width: parent.width
                        editable: false

                        function ensureListWithEntries()
                        {
                            var versions = manager.getVersionsList();
                            var version = 0;
                            model.clear();
                            
                            for(var i = 0; i < versions.length; ++i)
                            {
                                version = versions[i];
                                model.append({ text: manager.getFriendlyName(version), code: version });
                            }
                            currentIndex = 0;
                            updateCheckBoxes(model.get(currentIndex).code);
                        }

                        function updateCheckBoxes(rev_code)
                        {
                            checkCOMFound.checked = manager.getTechnicalInfoPerVersion(rev_code, "COM registered");
                            checkExecutableFound.checked = manager.getTechnicalInfoPerVersion(rev_code, "Executable found");
                            checkCOMStarting.checked = manager.getTechnicalInfoPerVersion(rev_code, "COM starting");
                            checkRevisionVerified.checked = manager.getTechnicalInfoPerVersion(rev_code, "Revision number");
                            checkFunctions.checked = manager.getTechnicalInfoPerVersion(rev_code, "Functions available");
                        }

                        onActivated:
                        {
                            updateCheckBoxes(model.get(index).code);
                        }
                        
                        Component.onCompleted: {
                            ensureListWithEntries();
                        }

                        model: ListModel
                        {
                            id: installationsModel
                            
                            Component.onCompleted:
                            {
                                append({ text: "- Nothing found -", code: -3 });
                            }
                        }
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: checkCOMFound
                        text: catalog.i18nc("@label", "COM service found");
                        enabled: false;
                        checked: false;
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: checkExecutableFound
                        text: catalog.i18nc("@label", "Executable found");
                        enabled: false;
                        checked: false;
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: checkCOMStarting
                        text: catalog.i18nc("@label", "COM starting");
                        enabled: false;
                        checked: false;
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: checkRevisionVerified
                        text: catalog.i18nc("@label", "Revision number");
                        enabled: false;
                        checked: false;
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: checkFunctions
                        text: catalog.i18nc("@label", "Functions available");
                        enabled: false;
                        checked: false;
                    }
                }
            }
        }
    }

    rightButtons: [
        Button
        {
            id: ok_button
            text: catalog.i18nc("@action:button", "Save")
            onClicked:
            {
                conversionTab.qualityDropdown.saveQualityCode();
                conversionTab.installations.saveInstallationCode();
                UM.Preferences.setValue("cura_solidworks/show_export_settings_always", conversionTab.showWizard.checked);
                UM.Preferences.setValue("cura_solidworks/auto_rotate", conversionTab.autoRotate.checked);
                close();
            }
            enabled: true
        },
        Button
        {
            id: cancel_button
            text: catalog.i18nc("@action:button", "Cancel")
            onClicked:
            {
                close();
            }
            enabled: true
        }
    ]
}
