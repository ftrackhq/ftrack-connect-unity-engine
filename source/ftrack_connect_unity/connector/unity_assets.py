# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
import ftrack
import ftrack_api
from ftrack_client import GetUnityEngine, GetUnityEditor, GetSystem, log_error_in_unity
import ftrack_connect_unity
from ftrack_connect.connector import (FTAssetType, FTAssetHandlerInstance,
                                      FTComponent)

# misc
import json
import logging
import os
from rpyc import async_
import shutil


SUPPORTED_PACKAGES = ['.unitypackage', '.unitypack']
SUPPORTED_EXTENSIONS = ['.abc', '.fbx']

class GenericAsset(FTAssetType):
    def __init__(self):
        super(GenericAsset, self).__init__()
        self.logger = logging.getLogger(
            __name__ + '.' + self.__class__.__name__
        )

    def importAsset(self, iAObj=None):
        self.logger.debug('In GenericAsset.importAsset')

        if not self._validate_ftrack_asset(iAObj):
            raise Exception('Invalid asset. See console for details')
                
        # Ask for a destination directory (into the Unity project)
        dst_directory = os.path.abspath(self._get_asset_import_path(iAObj))
        
        # Make sure the directory exists
        if not dst_directory:
            dst_directory = self._select_directory()
            
        # Import the asset
        self._import_ftrack_component(iAObj, dst_directory, iAObj.options) 
 
    def changeVersion(self, iAObj=None, applicationObject=None):
        '''
        Change the version of the asset defined in *iAObj*
        and *applicationObject*
        '''
        if not self._validate_ftrack_asset(iAObj):
            return False
        
        asset_path = asset_path = GetUnityEditor().AssetDatabase.GUIDToAssetPath(applicationObject)
        if not asset_path:
            error_string = 'Cannot find a related asset path in the Asset Database'
            self.logger.error(error_string)
            
            # Also log to the Unity console
            log_error_in_unity(error_string)

            return False
        
        asset_full_path = GetSystem.IO().Path.GetFullPath(asset_path)
        if not asset_full_path:
            error_string = 'Cannot determine the full path for {}'.format(asset_path)
            self.logger.error(error_string)
            
            # Also log to the Unity console
            log_error_in_unity(error_string)
            return False
        
        dst_directory = os.path.split(asset_full_path)[0]
        
        # Import, without considering settings (preserve settings as they 
        # currently are)
        self._import_ftrack_component(iAObj, dst_directory, None)
        return True

    def publishAsset(self, publish_args, iAObj=None):
        '''
        Publish the asset defined by the provided *iAObj*.
        '''
        file_paths_dict = publish_args
        publishedComponents = []
        componentName = "reviewable_asset"
        componentPath = "{0}.{1}".format(
            file_paths_dict.get("movie_path"),
            file_paths_dict.get("movie_ext"))

        publishedComponents.append(
            FTComponent(
                componentname=componentName,
                path=componentPath
            )
        )
        return publishedComponents, 'Published ' + iAObj.assetType + ' asset'

    @classmethod
    def importOptions(cls):
        '''
        Return import options for the component
        '''
        # No option in the generic class
        return ''
    
    @classmethod
    def exportOptions(cls):
        '''
        Return export options for the component
        '''
        xml = """
        <tab name="Options" accepts="unity">
            <row name="Publish Reviewable" accepts="unity" enabled="False">
                <option type="checkbox" name="publishReviewable" value="True"/>
            </row>
        </tab>"""
        return xml

    def _get_asset_import_path(self, iAObj):
        ftrack_asset_version = ftrack.AssetVersion(iAObj.assetVersionId)
        task = ftrack_asset_version.getTask()
        task_links = ftrack_api.Session().query(
            'select link from Task where id is "{0}"'.format(task.getId())
        ).first()['link']
        
        relative_path = ""
        # remove the project
        task_links.pop(0)
        for link in task_links:
            relative_path += link['name'].replace(' ', '_')
            relative_path += '/'
        
        return "{0}/ftrack/{1}".format(
            GetUnityEngine().Application.dataPath, relative_path)
    
    def _select_directory(self):
        """
        Displays a system dialog for the user to pick a destination folder
        Returns the directory name as a string
        """
        # Always start in the Assets directory        
        assets_path = GetUnityEngine().Application.dataPath

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
            self.logger.error(error_string)
            
            # Also log to the Unity console
            log_error_in_unity(error_string)
            return False

        (_, src_filename) = os.path.split(iAObj.filePath)
        (_, src_extension) = os.path.splitext(src_filename)
        if (src_extension.lower() not in SUPPORTED_EXTENSIONS and 
            src_extension.lower() not in SUPPORTED_PACKAGES):
            error_string = 'ftrack does not support importing files with extension "{}"'.format(src_extension)
            self.logger.error(error_string)

            # Also log to the Unity console
            log_error_in_unity(error_string)
            return False
        
        return True

    def _import_ftrack_component(self, iAObj, dst_directory, options):
        '''
        Attempts to import the given component file.
        '''
        # Populate import options, if required
        if options:
            self._populate_options(options)

        (_, extension) = os.path.splitext(iAObj.filePath)
        extension = extension.lower()

        if extension in SUPPORTED_EXTENSIONS:
            self._import_unity_asset_component(iAObj, dst_directory, options)
        elif extension in SUPPORTED_PACKAGES:
            self._import_unitypackage_component(iAObj, options)
        else:
            raise ValueError('file type : {} is not supported'.format(extension))
    
    def _import_unity_asset_component(self, iAObj, dst_directory, options):
        # The destination directory must be set
        if not dst_directory:
            error_string = 'ftrack cannot import the asset since the destination directory is missing'
            self.logger.error(error_string)
            
            # Also log to the Unity console
            log_error_in_unity(error_string)
            raise ValueError(error_string)

        # Prepare the Unity asset metadata
        asset_data = {
            'assetName': iAObj.assetName,
            'assetType': iAObj.assetType,
            'assetVersion': iAObj.assetVersion,
            'assetVersionId': iAObj.assetVersionId,
            'componentName': iAObj.componentName,
            'componentId': iAObj.componentId,
            'filePath': iAObj.filePath,
            'ftrack_connect_unity_version': ftrack_connect_unity.__version__
        }

        # Importing an asset can be a long process. We do not want the client to
        # be blocked, waiting on the server for too long. Connection timeouts
        # could occur, leading to import failures.
        #
        # Let the server do the work
        # Also pass all the arguments as a single json string. This 
        # minimizes the load on the socket (synchronizing the dictionaries)
        arguments = {
            'asset_data'   : asset_data,
            'options'      : options,
            'dst_directory': dst_directory
        }
        import_asset = async_(GetUnityEditor().Ftrack.ConnectUnityEngine.ServerSideUtils.ImportAsset)
        import_asset(json.dumps(arguments))

    def _import_unitypackage_component(self, iAObj, options):
        import_package = async_(GetUnityEditor().AssetDatabase.ImportPackage)
        import_package(iAObj.filePath, False)

    def _populate_options(self, options):
        # Generic Assets do not modify the import options
        pass

class GeoAsset(GenericAsset):
    @classmethod
    def importOptions(cls):
        return '''
        <tab name="Options">
            <row name="Import Materials" accepts="unity">
                <option type="checkbox" name="unityImportMaterials" value="True"/>
            </row>
        </tab>
        '''
    def _populate_options(self, options):
        # Force importing without animation. Users can always change this
        # directly in the ModelImporter Inspector panel
        options['unityImportAnim'] = False

class AnimAsset(GenericAsset):
    @classmethod
    def importOptions(cls):
        return '''
        <tab name="Options">
            <row name="Loop Time" accepts="unity">
                <option type="checkbox" name="unityLoopTime" value="False"/>
            </row>
        </tab>
        '''

    def _populate_options(self, options):
        # Force importing without materials. Users can always change this
        # directly in the ModelImporter Inspector panel
        options['unityImportMaterials'] = False
        options['unityImportAnim'] = True

class RigAsset(GenericAsset):
    @classmethod
    def importOptions(cls):
        return '''
        <tab name="Options">
            <row name="Animation Type:" accepts="unity">
                <option type="combo" name="unityAnimType">
                    <optionitem name="Generic"/>
                    <optionitem name="None"/>
                    <optionitem name="Legacy"/>
                    <optionitem name="Human"/>
                </option>
            </row>
            <row name="Import Materials" accepts="unity">
                <option type="checkbox" name="unityImportMaterials" value="True"/>
            </row>
        </tab>
        '''
    def _populate_options(self, options):
        # Force importing without animation. Users can always change this
        # directly in the ModelImporter Inspector panel
        options['unityImportAnim'] = False

class ImageSequenceAsset(GenericAsset):
    @classmethod
    def exportOptions(cls):
        '''
        Return export options for the component
        '''
        xml = """
        <tab name="Options" accepts="unity">
            <row name="Publish Reviewable" accepts="unity" enabled="True">
                <option type="checkbox" name="publishReviewable" value="False"/>
            </row>
            <row name="Publish Current Scene" accepts="unity" enabled="True">
                <option type="checkbox" name="publishPackage" value="False"/>
            </row>
        </tab>"""
        return xml

    def publishAsset(self, publish_args, iAObj=None):
        '''
        Publish the asset defined by the provided *iAObj*.
        '''
        file_paths_dict = publish_args
        publishReviewable = iAObj.options.get('publishReviewable')
        publishedComponents = []
        if publishReviewable:
            componentName = "reviewable_asset"
            componentPath = "{0}.{1}".format(
                file_paths_dict.get("movie_path"),
                file_paths_dict.get("movie_ext"))

            publishedComponents.append(
                FTComponent(
                    componentname=componentName,
                    path=componentPath
                )
            )

        imgComponentName = "image_sequence"

        # try to get start and end frames from env
        frameStart = os.environ.get("FS")
        frameEnd = os.environ.get("FE")

        # split image_path by <Frame>
        file_path_tokens = file_paths_dict.get(
            "image_path").split("<Frame>")
        imgComponentPath = "{0}%04d{1}.{2} [{3}-{4}]".format(
            file_path_tokens[0],
            file_path_tokens[1] if len(file_path_tokens) > 1 else '',
            file_paths_dict.get("image_ext"),
            frameStart,
            frameEnd)
        publishedComponents.append(
            FTComponent(
                componentname=imgComponentName,
                path=imgComponentPath
            )
        )

        # Publish the selection package if available
        publishPackage  = iAObj.options.get('publishPackage')
        if publishPackage:
            package_filepath = publish_args['package_filepath']
            package_filepath = os.path.normpath(package_filepath)
            publishedComponents.append(
                FTComponent(
                    componentname='package',
                    path=package_filepath
                )
            )

            # Track the assets being published
            dependencies = publish_args['package_dependencies']
            dependenciesVersion = []
            for path in dependencies:
                dependencyAssetId = self._get_asset_version_id(path)
                if dependencyAssetId:
                    dependencyVersion = ftrack.AssetVersion(dependencyAssetId)
                    dependenciesVersion.append(dependencyVersion)

            currentVersion = ftrack.AssetVersion(iAObj.assetVersionId)
            currentVersion.addUsesVersions(versions=dependenciesVersion)

        return (publishedComponents,
                'Published ' + iAObj.assetType + ' asset')
    
    def _get_asset_version_id(self, asset_path):
        # Get the importer for that asset
        asset_importer = GetUnityEditor().AssetImporter.GetAtPath(asset_path)
        
        # Get the metadata
        try:
            json_data = json.loads(asset_importer.userData)
        except:
            # Invalid or no user data.
            return None

        # Make sure this metadata is for ftrack by looking for this key
        if json_data.get('ftrack_connect_unity_version'):
            return json_data.get('assetVersionId')
        
        return None

def registerAssetTypes():
    assetHandler = FTAssetHandlerInstance.instance()
    assetHandler.registerAssetType(name='anim', cls=AnimAsset)
    assetHandler.registerAssetType(name='geo', cls=GeoAsset)
    assetHandler.registerAssetType(name='rig', cls=RigAsset)
    assetHandler.registerAssetType(name="img", cls=ImageSequenceAsset)
