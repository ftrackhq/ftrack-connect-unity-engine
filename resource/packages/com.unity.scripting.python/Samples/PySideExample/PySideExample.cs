using System.IO;
using UnityEditor;
using UnityEditor.Scripting.Python;
using UnityEngine;

public class PySideExample
{
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

    public static void OnHierarchyChanged()
    {
        // Notify the client that the hierarchy has changed
        PythonRunner.CallServiceOnClient("'on_hierarchy_changed'");
    }
}
