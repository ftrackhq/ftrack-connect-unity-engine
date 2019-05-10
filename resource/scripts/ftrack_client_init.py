# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

"""
This script is run on the client (remote process). It drives the 
QApplication where ftrack lives
"""


# Unity
import unity_client
from unity_client_service import UnityClientService

# ftrack
import ftrack
import ftrack_connect.config
from connector.unity_connector import Connector

# misc
import sys
import logging
import os

# globals
_connector = Connector()
_ftrack_is_initialized = False
_the_application = None
_ftrack_logger = None


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
        
        if _ftrack_logger:
            logger_method = getattr(_ftrack_logger, level)
            logger_method(msg)
    
def on_init_client(client):
    """
    Registers the custom rpyc service and the idle callback
    """
    # Install the ftrack logging handlers
    ftrack_connect.config.configure_logging('ftrack_connect_unity', level='DEBUG')

    # Create our logger
    global _ftrack_logger
    _ftrack_logger = logging.getLogger('ftrack_client')
    
    _ftrack_logger.debug('In on_init_client')

    client.register_idle_callback(on_idle)
    client.register_service(ftrackClientService)
    
def on_idle():
    """
    Processes the Qt events, if there is an application
    """
    try:
        from QtExt import QtGui
        QtGui.QApplication.instance().processEvents() 
    except Exception:
        pass

class ftrackClientService(UnityClientService):
    """
    Custom rpyc service that overrides the default Unity client service
    """
    def ftrack_load_and_init(self):
        try:
            Logger.debug('ftrackClientService.ftrack_load_and_init')

            global _ftrack_is_initialized
            if _ftrack_is_initialized:
                Logger.info('ftrack has already been initialized in the client process. Skipping initialization')
                return

            # Setup
            ftrack.setup()
            
            # Registration
            _connector.registerAssets()
            
            # We are done
            _ftrack_is_initialized = True
        except Exception as e:
            import traceback
            Logger.error('Got an exception: {}'.format(e))
            Logger.error('Stack trace:\n\n{}'.format(traceback.format_exc()))
        
    def ftrack_show_dialog(self, dialog_name):
        try:
            Logger.debug('ftrackClientService.ftrack_show_dialog: dialog_name = {}'.format(dialog_name))
            from QtExt import QtGui, QtCore
            
            # Make sure we have a valid application object
            global _the_application
            if not _the_application:
                _the_application = QtGui.QApplication([])
    
            ftrack_dialog = None
            if dialog_name == 'Info':
                from ftrack_connect.ui.widget.info import FtrackInfoDialog
                ftrack_dialog = FtrackInfoDialog(connector=_connector)
                
            if ftrack_dialog:
                # Since ftrack is running in a separate process, its dialogs 
                # tend to pop up behind Unity. This is why we set the 
                # stay-on-top flag.
                ftrack_dialog.setWindowFlags(ftrack_dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
                
                ftrack_dialog.show()
    
        except Exception as e:
            import traceback
            Logger.error('Got an exception: {}'.format(e))
            Logger.error('Stack trace:\n\n{}'.format(traceback.format_exc()))
