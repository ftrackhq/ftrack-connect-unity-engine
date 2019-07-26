# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack
"""
This script generates the C# script responsible to populate the menus in Unity
"""

# Unity
import unity_connection

# ftrack
from connector.unity_connector import UnityEngine, UnityEditor

# Misc
import os

# list of menu items that will show up in Unity, under the 'ftrack' menu
#     tuples: (menu_name, dialog_name)
# menu_name is the string that is displayed in the menu
# dialog_name is the dialog name as understood by ftrack_client_init.ftrackClientService.ftrack_show_dialog
_menu_items = [
    ('Info', 'Info'),
    ('Import asset', 'Import asset'),
    ('Publish', 'Publish'),
    ('Asset manager', 'Asset manager')
    ]

_script_template = '''
// Copyright (c) 2019 ftrack
using UnityEngine;
using UnityEditor.Scripting.Python;

namespace UnityEditor.ftrack.connect_unity_engine
{{
    public static class FtrackMenus
    {{
        {menu_item_section}
    }}
}}
'''

_menu_item_template = '''
        [MenuItem("ftrack/{menu_item_name}")]
        private static void ShowDialog{menu_item_index}()
        {{
            PythonRunner.CallServiceOnClient("'ftrack_show_dialog'", "'{dialog_name}'");
        }}
'''

_assembly_template = '''
{
    "name": "FtrackMenus",
    "references": [
        "Unity.Scripting.Python.Editor"
    ],
    "optionalUnityReferences": [],
    "includePlatforms": [
        "Editor"
    ],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": true,
    "defineConstraints": []
}
'''

_readme_template = '''
The Assets/ftrack folder files are generated from scratch every time ftrack 
initializes.

Do not use it to store your project assets as the folder will be deleted 
frequently.
'''
 
def generate():
    # Start by generating the menu item section
    menu_item_section = ''
    menu_item_index = 0
    for (menu_item_name, dialog_name) in _menu_items:
        menu_item_section += _menu_item_template.format(
            menu_item_name = menu_item_name, 
            dialog_name = dialog_name, 
            menu_item_index = menu_item_index)
        menu_item_index += 1
    
    # Then generate the full script
    script = _script_template.format(menu_item_section = menu_item_section)
    
    # Build the final file path
    ftrack_asset_path = UnityEngine().Application.dataPath
    ftrack_asset_path = os.path.normpath(
        os.path.join(ftrack_asset_path, 'ftrack', 'Temp'))

    script_path = os.path.join(ftrack_asset_path, 'FtrackMenus.cs')
    script_path = os.path.normpath(script_path)
    
    try:
        # Create the ftrack directory
        os.makedirs(ftrack_asset_path)
    except:
        # The directory already exists
        pass
    
    # Write the script    
    with open(script_path, 'w') as f:
        f.write(script)
        
    # Write the assembly definition
    assembly_definition_path = os.path.join(ftrack_asset_path, 'FtrackMenus.asmdef')
    assembly_definition_path = os.path.normpath(assembly_definition_path)
    with open(assembly_definition_path, 'w') as f:
        f.write(_assembly_template)
    
    # Write the README.txt file
    readme_path = os.path.join(ftrack_asset_path, 'README.txt')
    readme_path = os.path.normpath(readme_path)
    with open(readme_path, 'w') as f:
        f.write(_readme_template)
        
    # Refresh the database
    UnityEditor().AssetDatabase.Refresh()
