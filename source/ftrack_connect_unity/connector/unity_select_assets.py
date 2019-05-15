import UnityEditor
import UnityEngine
import System

assets_to_select = []

# Validate assets guids first
for guid in guids_to_select:
    asset_path = UnityEditor.AssetDatabase.GUIDToAssetPath(guid)
    if not asset_path:
        continue
        
    asset = UnityEditor.AssetDatabase.LoadMainAssetAtPath(asset_path)
    if asset:
        assets_to_select.append(asset)

# Select the objects   
UnityEditor.Selection.objects = System.Array[UnityEngine.Object](assets_to_select)

# Highlight the objects (ping)
# This does not work well on multi-selection (only the last element will be 
# highlighted). However pinging objects trigger a redraw of the UI and the final
# selection will be the expected one. Without a call to ping, the UI does not 
# redraw. We keep this code so the selection looks correct to the user.
for asset in assets_to_select:
    UnityEditor.EditorGUIUtility.PingObject(asset)
