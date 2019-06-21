# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
import ftrack_connect.config
from ftrack_connect.connector import base as maincon
from ftrack_connect.connector import FTAssetHandlerInstance

# Unity
import unity_client
import unity_connection

# misc
import json
import logging
import os
import pprint

# Install the ftrack logging handlers
ftrack_connect.config.configure_logging('ftrack_connect_unity', level='DEBUG')

"""
Unity C# API access

It is better to fetch the module each time we access it in case there was
a domain reload (the previous module would not be valid anymore)
"""
def UnityEngine():
    return unity_connection.get_module('UnityEngine')

def UnityEditor():
    return unity_connection.get_module('UnityEditor')

class System(object):
    @staticmethod
    def IO():
        return unity_connection.get_module('System.IO')

class Logger(object):
    """
    This class provides logging interface similar to the ftrack logger.
    Messages are printed to the client log, but also to the ftrack logger.
    
    We do this because the Unity Python package does not use the logging module
    yet. If it was, then it would use its own logger and handlers. Handlers 
    would be replaced by the ftrack handlers on init, which is fine.
    
    When everything is in place, we will be able to get rid of this class and 
    simply use our own logger directly (_ftrack_logger).
    
    Bottom-line, we want to write to both the logging module and the 
    unity_client module, until the unity_client module implements logging 
    properly. then we can get rid of this class.
    """
    # Create our logger
    _ftrack_logger = logging.getLogger('unity_connector')
    
    @classmethod
    def debug(cls, msg):
        cls._do_log(msg, 'debug')

    @classmethod
    def error(cls, msg):
        cls._do_log(msg, 'error')
    
    @classmethod
    def info(cls, msg):
        cls._do_log(msg, 'info')

    @classmethod
    def warning(cls, msg):
        cls._do_log(msg, 'warning')

    @classmethod
    def _do_log(cls, msg, level):
        client_msg = '[ftrack_client-{}] {}'.format(level, msg)
        unity_client.log(client_msg)
        
        ftrack_logger_method = getattr(cls._ftrack_logger, level)
        ftrack_logger_method(msg)

class Connector(maincon.Connector):
    def __init__(self):
        super(Connector, self).__init__()

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
    def getAssets():
        '''
        Return the available assets in the project, return the *componentId(s)*
        '''
        ftrack_assets = [ ]

        unity_asset_guids = UnityEditor().AssetDatabase.FindAssets('t:model', None)
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
    def getSelectedAssets():
        '''
        From the current selection in Unity, find what assets relate to ftrack
        assets and return a list of their Unity asset guids
        '''
        selected_ftrack_assets = []

        # Build a set of candidate guids
        # Look at currently selected assets in the project first
        guids = set(UnityEditor().Selection.assetGUIDs)
        
        # Then look at selected game objects in case they relate to ftrack 
        # assets
        for game_object in UnityEditor().Selection.gameObjects:
            asset_path = UnityEditor().PrefabUtility.GetPrefabAssetPathOfNearestInstanceRoot(game_object)
            if asset_path:
                guid = UnityEditor().AssetDatabase.AssetPathToGUID(asset_path)
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
        
        # Setting the selection from a list is not supported on the client side
        # yet because of how rpyc translates C# generics. We need to run the
        # selection code on the server
        # (Taken from the Unity Python package sample
        selection_script = os.path.dirname(__file__)
        selection_script = os.path.join(selection_script, 'unity_select_assets.py')
                
        # Double up the backslashes so they do not become escape characters
        selection_script = selection_script.replace('\\', '\\\\')
        
        # Execute the selection script, passing the guids as the globals 
        # dictionary
        unity_connection.execute('execfile("{}", {})'.format(selection_script, str( {'guids_to_select':guids} )))
    
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
        asset_path = asset_path = UnityEditor().AssetDatabase.GUIDToAssetPath(applicationObject)
        if not asset_path:
            return
        
        UnityEditor().AssetDatabase.DeleteAsset(asset_path)

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
        asset_path = UnityEditor().AssetDatabase.GUIDToAssetPath(guid)
        
        # Get the importer for that asset
        asset_importer = UnityEditor().AssetImporter.GetAtPath(asset_path)
        
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
