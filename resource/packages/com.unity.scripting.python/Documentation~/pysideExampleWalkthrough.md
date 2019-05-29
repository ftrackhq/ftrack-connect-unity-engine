# PySide Example Walkthrough

A simple PySide application can be found under the Python for Unity 
`Samples/PySideExample` directory. It can be launched by the 
`Python/Examples/PySide Example` menu. When launched, the following dialog shows
up:

![The PySide Example Dialog](images/pysideexample.png)

The dialog lists all the cameras in the current scene. It refreshes the list of 
cameras as they get added/removed to the scene. Selecting a camera and clicking 
the "Use Camera" button will set the Unity Editor Scene View to the selected 
camera.

The following section analyzes how the various pieces work together to achieve 
this result.

## PySide Setup

The sample requires that the PySide package is installed.
To do so, open a command prompt/shell and change directory to your Python 
installation/Scripts (on Windows, typicall located at c:\Python27\Scripts). Then 
type the following command:

```
pip install PySide
```

See [Validating Your Python Installation](validatingPython.html) to know how to 
validate your Python installation (Python, RPyC and PySide).

## The Client Init Module

The PySideExample is launched from Unity using this code (in `PySideExample.cs`)

```
    [MenuItem("Python/Examples/PySide Example")]
    public static void OnMenuClick()
    {
        // Start the Unity server and pass our client init module to the client
        string client_init_module_path = Path.GetFullPath("Packages/com.unity.scripting.python");
        client_init_module_path = Path.Combine(client_init_module_path, "Samples", "PySideExample", "PySideExample.py");
        PythonRunner.StartServer(client_init_module_path);
        PythonRunner.CallServiceOnClient("'show_dialog'");

        // Register to hierarchy changes on the server side 
        EditorApplication.hierarchyChanged += OnHierarchyChanged;
    }
```

You can see that PythonRunner.StartServer is given an extra parameter: 
`client_init_module_path`. The Client Init Module is a Python script that must 
provide a global function having this signature:  
```
def on_init_client(client):
```
This function is called when the client process initializes. In the PySide 
Example, its implementation is:

```
def on_init_client(client):
    """
    This function is the entry point called by the unity_client module on 
    client startup (from the main thread)
    
    It registers the custom rpyc service and the idle callback
    """
    log('In on_init_client')
   
    client.register_idle_callback(on_idle)
    client.register_service(PySideTestClientService)
```

This achieves 2 things:
* An idle callback is registered via the passed UnityClient instance
* A custom RPyC service is registered via the passed UnityClient instance

Note that the code should be minimal and very efficient in `on_init_client`. It
is blocking the client initialization and the server needs the client to 
initialize quickly. Also, calls into the Unity Scripting API cannot be made from 
the client module init function as the connection to the Unity process (server)
has not been established yet. 

This is why the Pyside Example creates its UI in a separate call to 
_PythonRunner.CallServiceOnClient("'show_dialog'")_. See details about 
[PythonRunner.CallServiceOnClient](pysideExampleWalkthrough.html#pythonrunnercallserviceonclient) below.

## UnityClient.register_idle_callback

This method registers an idle callback. The client process will periodically 
invoke the given callback at a maximum rate of once every millisecond.

In its implementation, the PySide Example simply processes the pending Qt Events:
```
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
```

This allows the dialog to process events like mouse clicks and redraws.

## UnityClient.register_service

This allows the client process to accept specific remote procedure calls, as 
explained in the [RPyC documentation](https://rpyc.readthedocs.io/en/latest/docs/services.html#services).

We saw in [Using the Out-of-Process API](outOfProcessAPI.html) how to run code 
or files in the client process. A third way of executing Python code in the 
client process is to call `PythonRunner.CallServiceOnClient`.

The PySide example registers a service class named `PySideTestClientService`:

```
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
```

## PythonRunner.CallServiceOnClient

The `on_hierarchy_changed` and `show_dialog` methods in the code above are new 
services exposed to RPyC. `on_server_stop` simply overrides the parent class 
behavior to make sure the application frees its UI on client stop (otherwise the
client would not exit gracefully)

The PySide example uses the newly exposed `on_hierarchy_changed` service when a 
hierachy change event occurs in Unity:
```
    public static void OnHierarchyChanged()
    {
        // Notify the client that the hierarchy has changed
        PythonRunner.CallServiceOnClient("'on_hierarchy_changed'");
    }
```

## Limitations
Sometimes RPyC cannot exchange all the information required by the client to 
fully use the Unity Scripting API. There is such a case in the PySide Example, 
when users click on the "Use Camera" button. The PySide Example needs to change 
the current scene selection for the selected camera. Ideally, the client would 
run this Python code:
```
UnityEditor = unity_connection.get_module('UnityEditor')
System = unity_connection.get_module('System')
selection = 
UnityEditor.Selection.instanceIDs = System.Array[int]([camera_id])
```

Unfortunately, running this code in the client process raises the following 
exception:
```
TypeError: descriptor '__getitem__' requires a 'Array' object but received a 'type'
```

The workaround in that case is to run the Python code on the server side, like 
it is done in the PySide example:
```
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
```
