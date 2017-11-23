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
    minimumWidth: Math.floor(screenScaleFactor * 365);
    // maximumWidth: width;

    height: Math.floor(screenScaleFactor * 180);
    minimumHeight: Math.floor(screenScaleFactor * 180);
    // maximumHeight: height;

    title: catalog.i18nc("@title:window", "SolidWorks plugin: Configuration")

    onVisibilityChanged:
    {
        if (visible)
        {
            installationsDropdown.fillInstallationListWithEntries();
            choiceDropdown.updateCurrentIndex();
            rememberChoiceCheckBox.checked = UM.Preferences.getValue("cura_solidworks/show_export_settings_always");
            autoRotateCheckBox.checked = UM.Preferences.getValue("cura_solidworks/auto_rotate");
        }
    }

    TabView {
        anchors.fill: parent
        UM.I18nCatalog{id: catalog; name: "SolidWorksPlugin"}

        Tab {
            title: catalog.i18nc("@title:window", "Conversion settings")
            GridLayout
            {
                Layout.fillWidth: true
                columnSpacing: 16 * screenScaleFactor
                rowSpacing: 10 * screenScaleFactor
                columns: 1

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
                        id: choiceDropdown

                        currentIndex: updateCurrentIndex()
                        width: 225 * screenScaleFactor

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

                        model: ListModel
                        {
                            id: choiceModel

                            Component.onCompleted:
                            {
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
                        id: rememberChoiceCheckBox
                        text: catalog.i18nc("@text:window", "Show wizard before opening SolidWorks files");
                        checked: UM.Preferences.getValue("cura_solidworks/show_export_settings_always");
                    }
                }
                Row
                {
                    width: parent.width
                    CheckBox
                    {
                        id: autoRotateCheckBox
                        text: catalog.i18nc("@text:window", "Automatically rotate opened file into normed orientation");
                        checked: UM.Preferences.getValue("cura_solidworks/auto_rotate");
                    }
                }
            }
        }
        Tab {
            title: catalog.i18nc("@title:tab", "BLA");
            GridLayout
            {
                Layout.fillWidth: true
                columnSpacing: 16 * screenScaleFactor
                rowSpacing: 10 * screenScaleFactor
                columns: 1

                Row {
                    width: parent.width

                        Label {
                            text: catalog.i18nc("@action:label", "Installation(s):");
                            width: 100 * screenScaleFactor
                            anchors.verticalCenter: parent.verticalCenter
                        }

                    ComboBox
                    {
                        id: installationsDropdown
                        currentIndex: 0
                        width: 242 * screenScaleFactor

                        function fillInstallationListWithEntries()
                        {
                            model.insert(1, { text: "SolidWorks 2016", code: 24 });
                        }

                        model: ListModel
                        {
                            id: installationsModel
                            Component.onCompleted:
                            {
                                append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Latest version (Recommended)"), code: 0 });
                                append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Default version"), code: 9999 });
                            }
                        }
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
                UM.Preferences.setValue("cura_solidworks/export_quality", choiceModel.get(choiceDropdown.currentIndex).code);
                UM.Preferences.setValue("cura_solidworks/show_export_settings_always", rememberChoiceCheckBox.checked);
                UM.Preferences.setValue("cura_solidworks/auto_rotate", autoRotateCheckBox.checked);
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
