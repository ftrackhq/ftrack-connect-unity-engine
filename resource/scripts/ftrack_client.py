# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

"""
This script is run on the client (remote process). It drives the 
QApplication where ftrack lives
"""

# ftrack
from connector.unity_connector import Connector
import ftrack
from ui import unity_menus

# Unity
import unity_python.client.unity_client as unity_client
import unity_python.common.scheduling as scheduling

# PySide
from QtExt import QtGui

# Misc
import logging
import os
from rpyc import async_
from rpyc.core.protocol import PingError
import rpyc.core.consts as consts
import socket
import sys
import time
import traceback

# globals
_connection = None
_connector = Connector()
_dialogs = []
_logger = logging.getLogger('ftrack_client')
_publish_dialog = None
_qapp  = None
_service = None

"""
C# API access

It is better to fetch the module each time we access it in case there was
a domain reload (the previous module would not be valid anymore)
"""
def GetUnityEngine():
    return _service.UnityEngine
def GetUnityEditor():
    return _service.UnityEditor
class GetSystem(object):
    @staticmethod
    def IO():
        return _service.import_module('System.IO')

# Logs an error in the Unity console. 
def log_error_in_unity(msg):
    # The following call is blocking (prone to 30-second lag issue)
    log_error = async_(GetUnityEngine().Debug.LogError)

    # The following is non-blocking
    log_error(msg)


class ftrackClientService(unity_client.UnityClientService):
    """
    Custom rpyc service that overrides the default Unity client service
    """
    def exposed_client_name(self):
        return "ftrack-connect-unity"

    def exposed_on_server_shutdown(self, invite_retry):
        if invite_retry:
            global _connection
            if _connection:
                _connection.close()
                _connection = None

            # Reconnect from the main thread. This will give the server time to
            # finish closing before we reconnect
            scheduling.call_on_main_thread(_connect_to_unity, wait_for_result = False)
        else:
            if _qapp:
                _qapp.quit()
            super(ftrackClientService, self).exposed_on_server_shutdown(invite_retry)

    @scheduling.exec_on_main_thread
    def exposed_publish(self, publish_args):
        global _publish_dialog
        _logger.debug('ftrackClientService.exposed_publish: publish_args) = {}'.format(publish_args))

        _publish_dialog.publishAsset(publish_args)

    @scheduling.exec_on_main_thread
    def exposed_show_dialog(self, dialog_name):
        try:
            _logger.debug('ftrackClientService.exposed_show_dialog: dialog_name = {}'.format(dialog_name))

            ftrack_dialog = None
            if dialog_name == 'Info':
                from ftrack_connector_legacy.ui.widget.info import FtrackInfoDialog
                ftrack_dialog = FtrackInfoDialog(connector=_connector)
                ftrack_dialog.setWindowTitle('Info')
            elif dialog_name == 'Import asset':
                from ftrack_connector_legacy.ui.widget.import_asset import FtrackImportAssetDialog
                ftrack_dialog = FtrackImportAssetDialog(connector=_connector)
                ftrack_dialog.setWindowTitle('ImportAsset')
                
                # Make the dialog bigger from its hardcoded values
                ftrack_dialog.setMinimumWidth(800)
                ftrack_dialog.setMinimumHeight(600)
            elif dialog_name == 'Asset manager':
                from ftrack_connector_legacy.ui.widget.asset_manager import FtrackAssetManagerDialog
                ftrack_dialog = FtrackAssetManagerDialog(connector=_connector)
                ftrack_dialog.setWindowTitle('AssetManager')
            elif dialog_name == 'Publish':
                from ftrack_connect_unity.ui.publisher import FtrackPublishDialog
                ftrack_dialog = FtrackPublishDialog(connector=_connector)
                ftrack_dialog.setWindowTitle('Publish')
                global _publish_dialog
                _publish_dialog = ftrack_dialog
            else:
                error_string = 'Invalid dialog name: "{}"'.format(dialog_name) 
                _logger.error(error_string)
                
                # Also log in the console
                GetUnityEngine().Debug.LogError(error_string)
                

            if ftrack_dialog:
                ftrack_dialog.show()

                # Keep a reference on the created dialogs so they do not vanish                
                _dialogs.append(ftrack_dialog)
    
        except Exception as e:
            _logger.exception('Got an exception while trying to show the "{}" ftrack dialog'.format(dialog_name))

class ftrackClientException(Exception):
    pass

def _sync_recorder_values():
    # The hook must provide us with start/end values
    frame_start = os.environ.get('FS')
    frame_end = os.environ.get('FE')
    
    try:
        shot_id = os.getenv('FTRACK_SHOTID')
        shot = ftrack.Shot(id = shot_id)
        fps = shot.get('fps')
    except Exception:
        fps = 24
    
    _logger.debug('Setting Unity Recorder values:'
        '\nFrame start: {0}\nFrame end: {1}\nFPS: {2}'.format(frame_start, frame_end, fps)
    )

    # Sync the values        
    GetUnityEditor().Ftrack.MovieRecorder.ApplySettings(
        int(float(frame_start)), int(float(frame_end)), fps
    )

def _initialize_ftrack():
    _logger.debug('Initializing ftrack in the client process')

    # Setup
    ftrack.setup()
    
    # Registration
    _connector.registerAssets()
    
    # Create the menus
    unity_menus.generate()
    
    # Synchronize the recorder to the shot associated
    # with the context (if relevant)
    _sync_recorder_values()

def _connect_to_unity():
    global _connection
    for i in range(120):
        # Give some time to the server to start listening
        time.sleep(2)
        try:
            _logger.info('Connecting to Unity')
            _connection = unity_client.connect(_service)
        except socket.error:
            _logger.info('Socket error')
            pass
        except EOFError:
            _logger.info('Connection lost, exiting')
            sys.exit('Unity has quit or the server closed unexpectedly')
        else:
            _logger.info('Connected')
            break

    if not _connection:
        exc_msg = 'Could not connect to Unity'
        _logger.error(exc_msg)
        raise ftrackClientException(exc_msg)

# There is an existing issue with the Python for Unity package where the 
# server waits for a client message. If no message comes in, the server
# will wait for 30 seconds and raise a timeout exception. No data is lost
# but the result is a 30-second delay. Pinging the server every second will
# reduce the lag to 1 second
last_ping_time = time.time()
def ping_server():
    global last_ping_time
    if time.time() - last_ping_time > 1.0:
        try:
            if _connection:
                _connection.async_request(consts.HANDLE_PING, "abcde")
        except PingError, EOFError:
            # We pass timeout = None to ping() so  we do not expect an
            # answer from the server. Swallow this exception
            #
            # We also swallow EOFError in case the connection gets momentarily
            # closed (domain reload)
            pass

        last_ping_time = time.time()

def main():
    global _service
    _logger.debug('In main')

    # Instantiate the service object
    _service = ftrackClientService()

    # Create the application
    global _qapp
    _qapp = QtGui.QApplication([])

    # Initialize scheduling
    scheduling.initialize()

    # Connect to Unity
    _connect_to_unity()

    # Initialize ftrack
    _initialize_ftrack()

    while (True):
        _qapp.processEvents()
        scheduling.process_jobs()

        ping_server()
        
        time.sleep(0.01)

if __name__ == '__main__':
    import ftrack_client
    ftrack_client.main()
    
