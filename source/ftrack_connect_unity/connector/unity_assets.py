# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
import ftrack_connect_unity
from ftrack_connect.connector import FTAssetType, FTAssetHandlerInstance
from connector.unity_connector import UnityEngine, UnityEditor, System, Logger

# misc
import json
import os

class GeometryAsset(FTAssetType):
    def __init__(self):
        super(GeometryAsset, self).__init__()

    def importAsset(self, iAObj=None):
        Logger.debug('In GeometryAsset.importAsset')

        if not self._validate_ftrack_asset(iAObj):
            return
                
        # Ask for a destination directory (into the Unity project)
        dst_directory = self._select_directory()
        
        # Import the asset
        if not self._import_ftrack_asset(iAObj, dst_directory):
            return

        
    def changeVersion(self, iAObj=None, applicationObject=None):
        '''
        Change the version of the asset defined in *iAObj*
        and *applicationObject*
        '''
        if not self._validate_ftrack_asset(iAObj):
            return False
        
        asset_path = asset_path = UnityEditor().AssetDatabase.GUIDToAssetPath(applicationObject)
        if not asset_path:
            error_string = 'Cannot find a related asset path in the Asset Database'
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False
        
        asset_full_path = System.IO().Path.GetFullPath(asset_path)
        if not asset_full_path:
            error_string = 'Cannot determine the full path for {}'.format(asset_path)
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False
        
        dst_directory = os.path.split(asset_full_path)[0]
        
        if not self._import_ftrack_asset(iAObj, dst_directory):
            return False
    
        return True

    def publishAsset(self, iAObj=None):
        '''
        Publish the asset defined by the provided *iAObj*.
        '''
        Logger.debug('In Connector.publishAsset. Not implemented yet')

    def _select_directory(self):
        """
        Displays a system dialog for the user to pick a destination folder
        Returns the directory name as a string
        """
        # Always start in the Assets directory        
        assets_path = UnityEngine().Application.dataPath

        from QtExt import QtGui
        options = [
            QtGui.QFileDialog.DontResolveSymlinks,
            QtGui.QFileDialog.DontUseNativeDialog,
            QtGui.QFileDialog.ShowDirsOnly
        ]

        caption = "Select destination directory"
        file_mode = QtGui.QFileDialog.Directory

        dialog = QtGui.QFileDialog(parent=QtGui.QApplication.instance().activeWindow(), caption=caption, directory=assets_path)
        dialog.setLabelText(QtGui.QFileDialog.Accept, "Select")
        dialog.setLabelText(QtGui.QFileDialog.Reject, "Cancel")
        dialog.setFileMode(file_mode)

        for option in options:
            dialog.setOption(option)

        # Show the dialog
        if not dialog.exec_():
            return None

        # Return value is a list of strings, pick the first one
        dst_directory = dialog.selectedFiles()
        if dst_directory:
            dst_directory = os.path.abspath(dst_directory[0])

        return dst_directory

    def _validate_ftrack_asset(self, iAObj=None):
        # Validate the file
        if not os.path.exists(iAObj.filePath):
            error_string = 'ftrack cannot import file "{}" because it does not exist'.format(iAObj.filePath)
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False

        # Only fbx files are supported
        (_, src_filename) = os.path.split(iAObj.filePath)
        (_, src_extension) = os.path.splitext(src_filename)
        if src_extension.lower() != '.fbx':
            error_string = 'ftrack does not support importing files with extension "{}"'.format(src_extension)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False
        
        return True

    def _import_ftrack_asset(self, iAObj, dst_directory):
        # The destination directory must exist
        if not os.path.isdir(dst_directory):
            error_string = 'ftrack cannot import into the chosen directory "{}"'.format(dst_directory)
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False
        
        # The destination directory must be under Assets/
        assets_path = UnityEngine().Application.dataPath
        assets_path = os.path.abspath(assets_path)
        if assets_path not in dst_directory:
            error_string = 'ftrack cannot import into a directory that is not under Assets/'
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False
        
        # Copy the file
        import shutil
        try:
            shutil.copy2(iAObj.filePath, dst_directory)
        except IOError as e:
            error_string = 'ftrack could not copy "{}" into "{}": {}'.format(iAObj.filePath, dst_directory, e)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False

        # Refresh the asset database
        UnityEditor().AssetDatabase.Refresh()
        
        # Add the ftrack metadata to the model importer
        # The Asset Importer expects a path using forward slashes and starting 
        # with 'Assets/'
        (_, src_filename) = os.path.split(iAObj.filePath)
        asset_importer_path = os.path.join(dst_directory, src_filename)
        asset_importer_path = asset_importer_path.replace('\\','/')
        asset_importer_path = asset_importer_path[asset_importer_path.find('/Assets')+1:]
        
        asset_importer = UnityEditor().AssetImporter.GetAtPath(asset_importer_path)
        if not asset_importer:
            error_string = 'Could not find the asset importer for {}'.format(asset_importer_path)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return False
        
        json_data = {
            'assetName'                    : iAObj.assetName,
            'assetType'                    : iAObj.assetType,
            'assetVersion'                 : iAObj.assetVersion,
            'assetVersionId'               : iAObj.assetVersionId,
            'componentName'                : iAObj.componentName,
            'componentId'                  : iAObj.componentId,
            'filePath'                     : iAObj.filePath,
            'ftrack_connect_unity_version' : ftrack_connect_unity.__version__
        }

        asset_importer.userData = json.dumps(json_data)
        asset_importer.SaveAndReimport()

        debug_string = 'Imported {} ({} -> {})'.format(src_filename, iAObj.filePath, dst_directory)
        Logger.debug(debug_string)
        
        # Also log to the Unity console
        UnityEngine().Debug.Log(debug_string)

        return True


def registerAssetTypes():
    assetHandler = FTAssetHandlerInstance.instance()
    assetHandler.registerAssetType(name='geo', cls=GeometryAsset)
