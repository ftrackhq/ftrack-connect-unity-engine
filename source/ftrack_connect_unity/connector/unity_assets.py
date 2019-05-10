# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
from ftrack_connect.connector import FTAssetType, FTAssetHandlerInstance
from connector.unity_connector import Logger

# Unity
import unity_connection

# misc
import os

def UnityEngine():
    """
    It is better to fetch the module each time we access it in case there was
    a domain reload (the previous module would not be valid anymore)
    """
    return unity_connection.get_module('UnityEngine')

def UnityEditor():
    """
    It is better to fetch the module each time we access it in case there was
    a domain reload (the previous module would not be valid anymore)
    """
    return unity_connection.get_module('UnityEditor')

class GeometryAsset(FTAssetType):
    def __init__(self):
        super(GeometryAsset, self).__init__()

    def importAsset(self, iAObj=None):
        Logger.debug('In GeometryAsset.importAsset')
        
        # Validate the file
        if not os.path.exists(iAObj.filePath):
            error_string = 'ftrack cannot import file "{}" because it does not exist'.format(iAObj.filePath)
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return error_string

        # Only fbx files are supported
        (_, src_filename) = os.path.split(iAObj.filePath)
        (_, src_extension) = os.path.splitext(src_filename)
        if src_extension.lower() != '.fbx':
            error_string = 'ftrack does not support importing files with extension "{}"'.format(src_extension)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return error_string
        
        # Ask for a destination directory (into the Unity project)
        dst_directory = self._select_directory()
        
        # Return value is a list of strings, pick the first one
        if dst_directory:
            dst_directory = os.path.abspath(dst_directory[0])

        # The destination directory must exist
        if not os.path.isdir(dst_directory):
            error_string = 'ftrack cannot import into the chosen directory "{}"'.format(dst_directory)
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return error_string
        
        # The destination directory must be under Assets/
        assets_path = UnityEngine().Application.dataPath
        assets_path = os.path.abspath(assets_path)
        if assets_path not in dst_directory:
            error_string = 'ftrack cannot import into a directory that is not under Assets/'
            Logger.error(error_string)
            
            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return error_string
        
        # Copy the file
        import shutil
        try:
            shutil.copy2(iAObj.filePath, dst_directory)
        except IOError as e:
            error_string = 'ftrack could not copy "{}" into "{}": {}'.format(iAObj.filePath, dst_directory, e)
            Logger.error(error_string)

            # Also log to the Unity console
            UnityEngine().Debug.LogError(error_string)
            return error_string

        # Refresh the asset database
        UnityEditor().AssetDatabase.Refresh()

        debug_string = 'Imported {} ({} -> {})'.format(src_filename, iAObj.filePath, dst_directory)
        Logger.debug(debug_string)
        
        # Also log to the Unity console
        UnityEngine().Debug.Log(debug_string)
        
    def changeVersion(self, iAObj=None, applicationObject=None):
        '''
        Change the version of the asset defined in *iAObj*
        and *applicationObject*
        '''
        Logger.debug('In Connector.changeVersion. Not implemented yet')

    def publishAsset(self, iAObj=None):
        '''
        Publish the asset defined by the provided *iAObj*.
        '''
        Logger.debug('In Connector.publishAsset. Not implemented yet')

    def _select_directory(self):
        """
        Displays a system dialog for the user to pick a destination folder
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

        return dialog.selectedFiles()

def registerAssetTypes():
    assetHandler = FTAssetHandlerInstance.instance()
    assetHandler.registerAssetType(name='geo', cls=GeometryAsset)
