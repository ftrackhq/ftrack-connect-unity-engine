# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack

import ftrack
import ftrack_api
import ftrack_connect.config
from ftrack_connect.connector import base as maincon
from ftrack_connect.connector import FTAssetHandlerInstance

# misc
import json
import logging
import os
import pprint

# Install the ftrack logging handlers
ftrack_connect.config.configure_logging('ftrack_connect_unity')

# Logging
_logger = logging.getLogger('unity_connector')

def GetUnityEditor():
    """
    We import ftrack_client here to avoid a circular dependency between
    ftrack_client and unity_connector
    """
    from ftrack_client import GetUnityEditor as ftGetUnityEditor
    return ftGetUnityEditor()
def GetUnityEngine():
    """
    We import ftrack_client here to avoid a circular dependency between
    ftrack_client and unity_connector
    """
    from ftrack_client import GetUnityEngine as ftGetUnityEngine
    return ftGetUnityEngine()

class Connector(maincon.Connector):
    def __init__(self):
        super(Connector, self).__init__()

    @staticmethod
    def getCurrentEntity():
        return ftrack.Task(
               os.getenv('FTRACK_TASKID'),
               os.getenv('FTRACK_SHOTID'))

    @staticmethod
    def isTaskPartOfShotOrSequence(currentTask):
        '''
        Return whether the given task is part of a shot
        or sequence.
        '''
        session = ftrack_api.Session()
        linksForTask = session.query(
            'select link from Task where id is "' +
            currentTask.getId() + '"'
        ).first()['link']
        # Remove task itself
        linksForTask.pop()
        linksForTask.reverse()
        parentShotSequence = None

        for item in linksForTask:
            entity = session.get(item['type'], item['id'])
            if entity.__class__.__name__ == 'Shot' or \
               entity.__class__.__name__ == 'Sequence':
                return True
        return False

    @classmethod
    def registerAssets(cls):
        '''
        Register all the available assets
        '''
        import unity_assets
        unity_assets.registerAssetTypes()
        super(Connector, cls).registerAssets()

    @staticmethod
    def importAsset(iAObj):
        '''
        Import the asset provided by *iAObj*
        '''
        asset_handler = FTAssetHandlerInstance.instance()
        import_asset = asset_handler.getAssetClass(iAObj.assetType)
        
        if import_asset:
            import_asset.importAsset(iAObj)
        else:
            Logger.warning('Asset Type "{}" not supported by the Unity connector'.format(iAObj.assetType))

    @staticmethod
    def publishAsset(published_file_path, iAObj=None):
        '''Publish the asset provided by *iAObj*'''
        assetHandler = FTAssetHandlerInstance.instance()
        pubAsset = assetHandler.getAssetClass(iAObj.assetType)
        if pubAsset:
            publishedComponents, message = pubAsset.publishAsset(published_file_path, iAObj)
            return publishedComponents, message
        else:
            return [], 'assetType not supported'

    @staticmethod
    def getAssets():
        '''
        Return the available assets in the project, return the *componentId(s)*
        '''
        ftrack_assets = [ ]

        unity_asset_guids = GetUnityEditor().AssetDatabase.FindAssets('t:model', None)
        for guid in unity_asset_guids:
            ftrack_asset = Connector._ftrack_asset_from_guid(guid) 
            if ftrack_asset:
                ftrack_assets.append(ftrack_asset)

        return ftrack_assets

    @staticmethod
    def changeVersion(applicationObject=None, iAObj=None):
        '''
        Change version of *iAObj* for the given *applicationObject*
        '''
        asset_handler = FTAssetHandlerInstance.instance()
        change_asset = asset_handler.getAssetClass(iAObj.assetType)
        if change_asset:
            result = change_asset.changeVersion(iAObj, applicationObject)
            return result
        else:
            Logger.warning('Asset Type "{}" not supported by the Unity connector'.format(iAObj.assetType))
            return False

    @staticmethod
    def getAsset(assetName, assetType, taskid):
        unity_asset_guids = GetUnityEditor().AssetDatabase.FindAssets('t:model', None)
        for guid in unity_asset_guids:
            # Get the asset path
            asset_path = GetUnityEditor().AssetDatabase.GUIDToAssetPath(guid)

            # Get the importer for that asset
            asset_importer = GetUnityEditor().AssetImporter.GetAtPath(asset_path)

            # Get the metadata
            try:
                json_data = json.loads(asset_importer.userData)
            except:
                # Invalid or no user data.
                continue

            # Make sure this is metadata is for ftrack by looking for this key
            if json_data.get('ftrack_connect_unity_version'):
                if json_data.get('assetName') == assetName and \
                   json_data.get('assetType') == assetType:
                    # We use the guid as the name (will be passed back as the
                    # applicationObject when changeVersion gets called
                    asset_version_id = json_data.get('assetVersionId')
                    asset_version = ftrack.AssetVersion(asset_version_id)
                    if asset_version.getTask().getId() == taskid:
                        return asset_version

        return None

    @staticmethod
    def getSelectedAssets():
        '''
        From the current selection in Unity, find what assets relate to ftrack
        assets and return a list of their Unity asset guids
        '''
        selected_ftrack_assets = []

        # Build a set of candidate guids
        # Look at currently selected assets in the project first
        guids = set(GetUnityEditor().Selection.assetGUIDs)
        
        # Then look at selected game objects in case they relate to ftrack 
        # assets
        for game_object in GetUnityEditor().Selection.gameObjects:
            asset_path = GetUnityEditor().PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(game_object)
            if asset_path:
                guid = GetUnityEditor().AssetDatabase.AssetPathToGUID(asset_path)
                if guid:
                    guids.add(guid)

        # Find which guids relate to ftrack assets 
        for guid in guids:
            ftrack_asset = Connector._ftrack_asset_from_guid(guid)
            if ftrack_asset:
                selected_ftrack_assets.append(guid)
            
        return selected_ftrack_assets
    
    @staticmethod
    def selectObjects(guids):
        '''
        Select the assets in the Unity project which match the current 
        Asset manager selection
        '''
        if len(guids) < 1:
            return

        # Select the assets
        GetUnityEditor().Ftrack.ConnectUnityEngine.ServerSideUtils.SelectObjectsWithGuids(guids)

    @staticmethod
    def selectObject(applicationObject):
        '''
        Select the Unity project asset which matches the asset manager's asset
        for which the 'S' button was clicked
        '''
        # Reuse the selectObjects method
        Connector.selectObjects([applicationObject])
            
    @staticmethod
    def removeObject(applicationObject):
        '''
        Delete the Unity project asset which matches the asset manager's asset
        for which the 'trash' button was clicked
        '''
        asset_path = asset_path = GetUnityEditor().AssetDatabase.GUIDToAssetPath(applicationObject)
        if not asset_path:
            return
        
        GetUnityEditor().AssetDatabase.DeleteAsset(asset_path)

    @staticmethod
    def getConnectorName():
        '''Return the connector name'''
        return 'unity'
        
    @staticmethod
    def _ftrack_asset_from_guid(guid):
        '''
        Helper method to go from one Unity asset guid to a tuple of 
        (ftrack componentId, Unity asset guid)
        '''
        # Get the asset path
        asset_path = GetUnityEditor().AssetDatabase.GUIDToAssetPath(guid)
        
        # Get the importer for that asset
        asset_importer = GetUnityEditor().AssetImporter.GetAtPath(asset_path)
        
        # Get the metadata
        try:
            json_data = json.loads(asset_importer.userData)
        except:
            # Invalid or no user data.
            return None 
        
        # Make sure this is metadata is for ftrack by looking for this key
        if json_data.get('ftrack_connect_unity_version'):
            # We use the guid as the name (will be passed back as the 
            # applicationObject when changeVersion gets called
            return ( (json_data.get('componentId'), guid) )
            
        return None
