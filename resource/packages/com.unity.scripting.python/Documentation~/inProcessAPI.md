# Using the In-Process API

The In-Process API is meant for scripts that are stateless, which means that 
they do not keep information between runs. This is because Unity often reloads
assemblies (during domain reload), and the Python for Unity assembly will 
re-initialize the Python interpreter when its assembly gets reloaded. This means 
anything that is stored in the Python interpreter will eventually get destroyed 
by the garbage collector.

Examples of scripts that are good candidates for the In-Process API are:
- Scripts processing scene data like creating, deleting or modifying assets
- Scripts using external scene description (EDL, json) in order to assemble a 
scene
- Validation scripts before pushing to production
- ...

Scripts that need to keep information, like scripts providing UI elements built 
with SDKs like PySide should use the [Out-of-Process API](outOfProcessAPI.html)
since these scripts need to survive assembly reloads.

## PythonRunner.RunString
The following C# code will create a menu item that prints "hello world" in the 
Unity console:

```
using UnityEditor.Scripting.Python;
using UnityEditor;

public class HelloWorld
{
    [MenuItem("Python/Hello World")]
    static void PrintHelloWorldFromPython()
    {
        PythonRunner.RunString(@"
import UnityEngine;
UnityEngine.Debug.Log('hello world')
");
    }
}
```

You can use any assembly that is available in C# by simply importing it with the
Python _import_ statement.

## PythonRunner.RunFile
Instead of inlining your Python code inside of a C# script, you can execute a 
whole Python script using the _PythonRunner.RunFile_ method. For example, this 
Python script loops over all the GameObjects in a scene and makes sure all the 
names end up with an underscore:

```
import UnityEngine

all_objects = UnityEngine.Object.FindObjectsOfType(UnityEngine.GameObject)
for go in all_objects:
    if go.name[-1] != '_':
        go.name = go.name + '_'
```

Script files can be located anywhere on your computer, and in this example we 
chose to put it under _Assets/ensure_naming.py_. You can run 
this Python script from C# the following way:

```
using UnityEditor.Scripting.Python;
using UnityEditor;
using UnityEngine;
using System.IO;

public class EnsureNaming
{
    [MenuItem("Python/Ensure Naming")]
    static void RunEnsureNaming()
    {
        string scriptPath = Path.Combine(Application.dataPath,"ensure_naming.py");
        PythonRunner.RunFile(scriptPath);
    }
}