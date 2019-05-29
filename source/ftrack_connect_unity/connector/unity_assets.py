# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
import ftrack_connect_unity
from ftrack_connect.connector import FTAssetType, FTAssetHandlerInstance
from connector.unity_connector import UnityEngine, UnityEditor, System, Logger

# misc
import json
import os
import shutil

class GenericAsset(FTAssetType):
    def __init__(self):
        super(GenericAsset, self).__init__()

    def importAsset(self, iAObj=None):
        Logger.debug('In GenericAsset.importAsset')

        if not self._validate_ftrack_asset(iAObj):
            raise Exception('Invalid asset. See console for details')
                
        # Ask for a destination directory (into the Unity project)
        dst_directory = self._select_directory()
        
        # Import the asset
        model_importer = self._import_ftrack_asset(iAObj, dst_directory) 
        if not model_importer:
            raise Exception('Could not import asset. See console for details')

        # Apply the right settings to the importer
        self._apply_settings_on_model_importer(model_importer)
        model_importer.SaveAndReimport()

        
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
        '''
        Attemps to import the give asset .fbx file
        Returns the model importer if successful, otherwise returns None
        '''
        # The destination directory must exist
        if not dst_directory or not os.path.isdir(dst_directory):
            error_string = 'ftrack cannot import into the chosen directory "{}"'.format(dst_directory)
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return None
        
        # The destination directory must be under Assets/
        assets_path = UnityEngine().Application.dataPath
        assets_path = os.path.abspath(assets_path)
        if assets_path not in dst_directory:
            error_string = 'ftrack cannot import into a directory that is not under Assets/'
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return None
        
        # Copy the file
        src_file = iAObj.filePath
        (_, extension) = os.path.splitext(src_file)

        # Use the asset name as the destination file name
        dst_file = os.path.join(dst_directory, iAObj.assetName)
        dst_file += extension
        dst_file = os.path.normpath(dst_file)
        try:
            shutil.copy2(src_file, dst_file)
        except IOError as e:
            error_string = 'ftrack could not copy "{}" into "{}": {}'.format(src_file, dst_file, e)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return None

        # Refresh the asset database
        UnityEditor().AssetDatabase.Refresh()
        
        # Add the ftrack metadata to the model importer
        # The Asset Importer expects a path using forward slashes and starting 
        # with 'Assets/'
        model_importer_path = dst_file
        model_importer_path = model_importer_path.replace('\\','/')
        model_importer_path = model_importer_path[model_importer_path.find('/Assets')+1:]
        
        model_importer = UnityEditor().AssetImporter.GetAtPath(model_importer_path)
        if not model_importer:
            error_string = 'Could not find the asset importer for {}'.format(model_importer_path)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return None
        
        json_data = {
            'assetName'                    : iAObj.assetName,
            'assetType'                    : iAObj.assetType,
            'assetVersion'                 : iAObj.assetVersion,
            'assetVersionId'               : iAObj.assetVersionId,
            'componentName'                : iAObj.componentName,
            'componentId'                  : iAObj.componentId,
            'filePath'                     : src_file,
            'ftrack_connect_unity_version' : ftrack_connect_unity.__version__
        }

        model_importer.userData = json.dumps(json_data)
        model_importer.SaveAndReimport()
        
        debug_string = 'Imported {} ({} -> {})'.format(iAObj.assetName, src_file, dst_file)
        Logger.debug(debug_string)
        
        # Also log to the Unity console
        UnityEngine().Debug.Log(debug_string)

        return model_importer

    def _apply_settings_on_model_importer(self, model_importer):
        # Disable Animation and Rigging
        model_importer.animationType = UnityEditor().ModelImporterAnimationType.None
        model_importer.importAnimation = False
        
        # Disable Materials
        model_importer.importMaterials = False
        

class AnimationAsset(GenericAsset):
    def _apply_settings_on_model_importer(self, model_importer):
        # Call the base class
        super(AnimationAsset, self)._apply_settings_on_model_importer(model_importer)
        
        # Enable animation
        model_importer.animationType = UnityEditor().ModelImporterAnimationType.Generic
        model_importer.importAnimation = True

class RigAsset(GenericAsset):
    def _apply_settings_on_model_importer(self, model_importer):
        # Call the base class
        super(RigAsset, self)._apply_settings_on_model_importer(model_importer)
        
        # Enable Rig
        model_importer.animationType = UnityEditor().ModelImporterAnimationType.Generic
        model_importer.importAnimation = False

def registerAssetTypes():
    assetHandler = FTAssetHandlerInstance.instance()
    assetHandler.registerAssetType(name="anim", cls=AnimationAsset)
    assetHandler.registerAssetType(name='geo', cls=GenericAsset)
    assetHandler.registerAssetType(name='rig', cls=RigAsset)