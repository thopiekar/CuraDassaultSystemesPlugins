// Copyright (c) 2017 Ultimaker B.V.
// Cura is released under the terms of the AGPLv3 or higher.

import QtQuick 2.1
import QtQuick.Controls 1.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.0 as Cura

UM.Dialog
{
    width: 300 * Screen.devicePixelRatio;
    minimumWidth: 300 * Screen.devicePixelRatio;

    height: 100 * Screen.devicePixelRatio;
    minimumHeight: 100 * Screen.devicePixelRatio;

    title: catalog.i18nc("@title:window", "SolidWorks: Export wizard")

    onVisibilityChanged:
    {
        if (visible)
        {
            qualityDropdown.currentIndex = 0;
            rememberChoiceCheckBox.checked = UM.Preferences.getValue("cura_solidworks/show_export_settings_always");
        }
    }

    GridLayout
    {
        UM.I18nCatalog{id: catalog; name: "SolidWorksPlugin"}
        anchors.fill: parent;
        Layout.fillWidth: true
        columnSpacing: 16
        rowSpacing: 4
        columns: 1

        UM.TooltipArea {
            Layout.fillWidth:true
            height: childrenRect.height
            text: catalog.i18nc("@info:tooltip", "Export settings")
            Row {
                width: parent.width

                Label {
                    text: catalog.i18nc("@action:label", "Quality")
                    width: 100
                    anchors.verticalCenter: parent.verticalCenter
                }

                ComboBox
                {
                    id: qualityDropdown
                    model: ListModel
                    {
                        id: qualityModel

                        Component.onCompleted:
                        {
                            append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Fine (SolidWorks)"), code: 10 });
                            append({ text: catalog.i18nc("@option:curaSolidworksStlQuality", "Coarse (SolidWorks)"), code: 0 });
                        }
                    }
                    currentIndex: 1
                }
            }
        }

        Row
        {
            width: parent.width

            CheckBox
            {
                id: rememberChoiceCheckBox
                text: catalog.i18nc("@text:window", "Remember my choice")
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
                manager.setQuality(qualityModel.get(qualityDropdown.currentIndex).code, rememberChoiceCheckBox.checked);
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
