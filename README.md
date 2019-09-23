# Limitations
The ftrack plug-in for Unity is only supported on Windows platforms.
Supported versions of Unity:
* 2018 LTS Release(Currently 2018.3)
* 2019 Release (Currently 2019.1)

# Installation

## Python
1. Start by installing [Python 2.7.15 (64 bits) or later](https://www.python.org/downloads/release/python-2716/). 
The package does not work with Python 3.
1. From a cmd prompt, type `python` and make sure the installed Python can be 
discovered. If not, adjust your `%PATH%` environment variable to include the path
where Python.exe resides.
1. In the Python interpreter, type the following code and make sure the returned value matches the directory where you installed Python:
```
>>> import sys
>>> print sys.executable
``` 
1. Quit the interpreter by typing
```
>>> quit()
```

## ftrack plug-in for Unity
1. (optional) In a cmd prompt, from the same location this README.md file resides, run 
`python setup.py build_plugin`
1. Copy the ftrack plugin (or the resulting `build/ftrack-connect-unity-engine-x.y.z`)
directory to the standard location, as described in 
https://help.ftrack.com/connect/getting-started-with-connect/installing-and-using-connect 
under *Customizing ftrack Connect* (Typically 
`C:\Users\<user_name>\AppData\Local\ftrack\ftrack-connect-plugins`)
1. Restart ftrack-connect

# Usage
1. In ftrack-connect, browse to a task. The Unity icon should appear in 
ftrack-connect and list all available versions of Unity. 
1. Select a version of Unity. The project selection window appears. 
Select / create a project and the editor will launch

# Setting up a Unity project
In order to work with a Unity project, the ftrack integration requires two 
packages to be installed: the Python package and the ftrack package. 

The Python package is located under the ftrack plug-in directory, in 
`resources/packages/com.unity.scripting.python.

1. Once Unity starts, use the `Window/Package Manager` menu to bring up the 
Package Manager
1. In the Package Manager window, locate the `+` sign, click on it, then 
select `Add package from disk...`
1. Browse to `<ftrack-connect-unity-engine>/resources/packages/com.unity.scripting.python`
1. Select the package.json file

The ftrack package is accessible from a Git URL:

1. In the Package Manager window, locate the `+` sign, click on it, then 
select `Add package from git URL...`
1. Enter the following URL: `https://bitbucket.org/ftrack/ftrack-connect-unity-plugin.git`

ftrack should initialize and a menu named `ftrack` should be available in Unity

Note: ftrack dialogs tend to show behind the Unity editor window.

# Troubleshooting
## Locating Unity installations
If selecting a task does not make the Unity logo appear, you can try to set the 
UNITY_LOCATION environment variable to point to a valid Unity.exe editor. 
Otherwise the following notes from the Unity hook should help you make sure your 
editors can be discovered:
```
If UNITY_LOCATION is specified in the environment, it will be the only 
listed editor. Otherwise we discover Unity installations using these 
locations:

1. The registry (HKEY_CURRENT_USER\Software\Unity Technologies\Installer).
   This includes all the versions of Unity that were installed using 
   the Hub
2. %APPDATA%\UnityHub\editors.json
   This includes all the installations that were added using the 
   "Locate a version" option in the Unity Hub
3. %APPDATA%\UnityHub\secondaryInstallPath.json
   This provides a root path where multiple versions of Unity might 
   exist
   
We use %APPDATA%\UnityHub\defaultEditor.json to determine the default 
editor. If we find the default editor we make it the first item of the 
list. 
```

## Unity 2019 and higher
When launching Unity 2019 and higher from ftrack-connect, the Unity Hub will 
appear. There is a limitation with the 
Unity Hub 2.0 which prevents ftrack from initializing properly. You need to 
stop all running "Unity Hub.exe" processes before launching Unity from 
ftrack-connect. This will be fixed by the Unity team in an upcoming release 
(tentative for Unity Hub 2.1)

## Package Manager is not available in Unity
If you cannot see the Package Manager menu item, make sure you installed 
[Microsoft Visual Studio Community](https://learn.unity.com/tutorial/get-started-with-visual-studio-and-unity)

Installing [.NET Core prerequisites](http://go.microsoft.com/fwlink/?LinkID=798306&clcid=0x409) 
might help resolve this problem

