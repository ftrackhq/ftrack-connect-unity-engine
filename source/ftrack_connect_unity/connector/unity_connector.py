# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
import ftrack_connect.config
from ftrack_connect.connector import base as maincon
from ftrack_connect.connector import FTAssetHandlerInstance

# Unity
import unity_client

# misc
import logging
import os
import pprint

# Install the ftrack logging handlers
ftrack_connect.config.configure_logging('ftrack_connect_unity', level='DEBUG')

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
            result = import_asset.importAsset(iAObj)
            return result
        else:
            return 'assetType not supported'
