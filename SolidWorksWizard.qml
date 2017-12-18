// Copyright (c) 2017 Ultimaker B.V.

import QtQuick 2.1
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.0 as Cura

UM.Dialog
{
    width: screenScaleFactor * 300;
    minimumWidth: width;
    maximumWidth: width;

    height: screenScaleFactor * 100;
    minimumHeight: height;
    maximumHeight: height;

    title: catalog.i18nc("@title:window", "SolidWorks: Export wizard")

    onVisibilityChanged:
    {
        if (visible)
        {
            qualityDropdown.updateCurrentIndex();
            showAgainCheckBox.checked = UM.Preferences.getValue("cura_solidworks/show_export_settings_always");
        }
    }

    GridLayout
    {
        UM.I18nCatalog{id: catalog; name: "SolidWorksPlugin"}
        anchors.fill: parent;
        Layout.fillWidth: true
        columnSpacing: 16 * screenScaleFactor
        rowSpacing: 4 * screenScaleFactor
        columns: 1

        Row {
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
                width: 175 * screenScaleFactor

                function updateCurrentIndex()
                {
                    var index = 10;
                    var currentQuality = UM.Preferences.getValue("cura_solidworks/export_quality");
                    for (var i = 0; i < model.count; ++i)
                    {
                        if (model.get(i).code == currentQuality)
                        {
                            index = i;
                            break;
                        }
                    }
                    currentIndex = index;
                }

                model: ListModel
                {
                    id: qualityModel

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
                id: showAgainCheckBox
                text: catalog.i18nc("@text:window", "Show this dialog again")
                checked: UM.Preferences.getValue("cura_solidworks/show_export_settings_always")
            }
        }
    }

    rightButtons: [
        Button
        {
            id: ok_button
            text: catalog.i18nc("@action:button", "Continue")
            onClicked:
            {
                UM.Preferences.setValue("cura_solidworks/export_quality", qualityModel.get(qualityDropdown.currentIndex).code);
                UM.Preferences.setValue("cura_solidworks/show_export_settings_always", showAgainCheckBox.checked);
                manager.onOkButtonClicked();
            }
            enabled: true
        },
        Button
        {
            id: cancel_button
            text: catalog.i18nc("@action:button", "Abort")
            onClicked:
            {
                manager.onCancelButtonClicked();
            }
            enabled: true
        }
    ]
}
