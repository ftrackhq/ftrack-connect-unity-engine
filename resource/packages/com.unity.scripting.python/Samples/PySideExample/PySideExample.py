"""
Example using PySide on the client to create a window showing the available cameras in the scene.
The user can select a camera and click "Use Camera" to set the Scene view to the viewport of the selected camera.
"""
import os
import sys
import traceback
import unity_connection

from unity_client_service import UnityClientService

try:
    from PySide import QtCore, QtGui, QtUiTools
except Exception as e:
    unity_connection.get_module("UnityEngine").Debug.LogError("Could not start the Python client (missing PySide package). Please refer to the com.unity.scripting.documentation on how to configure Python for Unity")
    raise e

### Globals
# The UI class
_pysideUI = None

### Logging
def log(msg):
    print "[pyside_example] {0}".format(msg)

### Helpers
def UnityEditor():
    """
    It is recommended to get the modules right before calling into them 
    as C# domain reloads could render them invalid. 
    Calling unity_connection.get_module retrieves a valid module at all times.
    
    Do not keep references on the returned module object. Fetch it again by 
    calling UnityEngine again before accessing it
    """
    return unity_connection.get_module("UnityEditor")
    
def UnityEngine():
    """
    See UnityEditor
    """
    return unity_connection.get_module("UnityEngine")

def System():
    """
    See UnityEditor
    """
    return unity_connection.get_module("System")

### Client Initialization
def on_init_client(client):
    """
    This function is the entry point called by the unity_client module on 
    client startup (from the main thread)
    
    It registers the custom rpyc service and the idle callback
    """
    log('In on_init_client')
   
    client.register_idle_callback(on_idle)
    client.register_service(PySideTestClientService)
    
def on_idle():
    """
    Called by the unity_client module, approximately every millisecond, if 
    possible
    
    Processes the Qt events, if there is an application
    """
    try:
        QtGui.QApplication.instance().processEvents() 
    except:
        pass

### Custom Client Service        
class PySideTestClientService(UnityClientService):
    """
    Custom rpyc service that overrides the default Unity client service.
    Makes it possible to make specific method calls from the server to the client
    """
    def on_hierarchy_changed(self):
        global _pysideUI
        log("In PySideTestClientService.on_hierarchy_changed")

        # Rebuild the UI on hierarchy change
        _pysideUI.populate_camera_list()
            
    def show_dialog(self):
        global _pysideUI
        log("In PySideTestClientService.show_dialog")

        # Create the UI class  
        _pysideUI = PySideTestUI()

    def on_server_stop(self, terminate_client):
        """
        override from the base class
        """
        global _pysideUI
        super(PySideTestClientService,self).on_server_stop(terminate_client)
        
        if terminate_client:
            # Release our reference to the UI when the client exits. This allows 
            # the client to exit gracefully 
            _pysideUI = None

### UI class            
class PySideTestUI():
    def __init__(self):
        # Initialize the application and the dialog
        self._qApp   = None
        self._dialog = None
        
        try:
            # Create the application if required
            self._qApp = QtGui.QApplication.instance()
            if not self._qApp:
                self._qApp = QtGui.QApplication(sys.argv)

            # Create the dialog from our .ui file
            ui_path = System().IO.Path.GetFullPath('Packages/com.unity.scripting.python');
            ui_path = os.path.join(ui_path, 'Samples', 'PySideExample', "PySideExample.ui");
            self._dialog = self.load_ui_widget(ui_path.replace("\\", "/"))
            
            # Initial population of the camera list
            self.populate_camera_list()

            # Show the dialog
            self._dialog.show()

        except Exception as e:
            log('Got an exception while creating the dialog:')
            log(traceback.format_exc())
            raise e
        
    def populate_camera_list(self):
        """
        Populates the list of cameras
        """
        cameraList = UnityEngine().Camera.allCameras

        listWidget = self._dialog.listWidget
        listWidget.clear()
        for cam in cameraList:
            listWidget.addItem(cam.name)
        
    def use_camera(self):
        if not self._dialog:
            return
            
        selectedItems = self._dialog.listWidget.selectedItems()
        if len(selectedItems) < 1:
            return
            
        try:
            camera = UnityEngine().GameObject.Find(selectedItems[0].text())
            self.select_camera(camera)
            
            UnityEditor().EditorApplication.ExecuteMenuItem("GameObject/Align View to Selected")
        except Exception as e:
            log('Got an exception trying to use the camera:')
            log(traceback.format_exc())
            raise e

    def load_ui_widget(self, uifilename, parent=None):
        loader = QtUiTools.QUiLoader()
        uifile = QtCore.QFile(uifilename)
        uifile.open(QtCore.QFile.ReadOnly)
        ui = loader.load(uifile, parent)
        uifile.close()
        
        ui.useCameraButton.clicked.connect(self.use_camera)
        
        return ui
        
    def select_camera(self, camera):
        id = camera.GetInstanceID()
        
        # Executing the camera selection on the server as it is not
        # currently possible to create the C# Array using generics
        # on the client.
        unity_connection.execute(
            """
import UnityEditor
import System
selList = [{id}]
selection = System.Array[int](selList)
UnityEditor.Selection.instanceIDs = selection
""".format(id=id))
    