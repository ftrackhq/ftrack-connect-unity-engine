# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

"""
This script is run on the client (remote process). It drives the 
QApplication where ftrack lives
"""


# Unity
from unity_client_service import UnityClientService

# ftrack
import ftrack
from connector.unity_connector import Connector
from connector.unity_connector import Logger

# globals
_connector = Connector()
_ftrack_is_initialized = False
_the_application = None
_dialogs = []

def on_init_client(client):
    """
    Registers the custom rpyc service and the idle callback
    """
    Logger.debug('In on_init_client')
    
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
                ftrack_dialog.setWindowTitle('Info')
            elif dialog_name == 'Import asset':
                from ftrack_connect.ui.widget.import_asset import FtrackImportAssetDialog
                ftrack_dialog = FtrackImportAssetDialog(connector=_connector)
                ftrack_dialog.setWindowTitle('ImportAsset')
                
                # Make the dialog bigger from its hardcoded values
                ftrack_dialog.setMinimumWidth(800)
                ftrack_dialog.setMinimumHeight(600)
            elif dialog_name == 'Asset manager':
                from ftrack_connect.ui.widget.asset_manager import FtrackAssetManagerDialog
                ftrack_dialog = FtrackAssetManagerDialog(connector=_connector)
                ftrack_dialog.setWindowTitle('AssetManager')

            if ftrack_dialog:
                # Since ftrack is running in a separate process, its dialogs 
                # tend to pop up behind Unity. This is why we set the 
                # stay-on-top flag.
                ftrack_dialog.setWindowFlags(ftrack_dialog.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
                
                ftrack_dialog.show()

                # Keep a reference on the created dialogs so they do not vanish                
                _dialogs.append(ftrack_dialog)
    
        except Exception as e:
            import traceback
            Logger.error('Got an exception: {}'.format(e))
            Logger.error('Stack trace:\n\n{}'.format(traceback.format_exc()))
