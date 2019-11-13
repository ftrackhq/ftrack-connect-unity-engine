..
    :copyright: Copyright (c) 2019 ftrack

.. _trubleshooting:


Trubleshooting
==============

Locating Unity installations
----------------------------

If selecting a task does not make the Unity logo appear, you can try to set the 
**%UNITY_LOCATION%** environment variable to point to a valid Unity.exe editor. 
Otherwise the following notes from the Unity hook should help you make sure your 
editors can be discovered:

If **%UNITY_LOCATION%** is specified in the environment, it will be the only 
listed editor. Otherwise we discover Unity installations using these 
locations:

1. The registry (**%HKEY_CURRENT_USER%\Software\Unity Technologies\Installer**).
   This includes all the versions of Unity that were installed using 
   the Hub

2. **%APPDATA%\UnityHub\editors.json**
   This includes all the installations that were added using the 
   "Locate a version" option in the Unity Hub

3. **%APPDATA%\UnityHub\secondaryInstallPath.json**
   This provides a root path where multiple versions of Unity might 
   exist
   
We use **%APPDATA%\UnityHub\defaultEditor.json** to determine the default 
editor. If we find the default editor we make it the first item of the 
list. 

Sporadic 30 seconds lag
-----------------------

There is a known, sporadic issue with the Python for Unity package where there
might be a 30 seconds delay between the time an operation is launched and when 
it is actually processed. This can happen, for example, when accessing the ftrack
menu items. The desired dialog might take 30 seconds before being displayed when
the issue arises.

Unity 2019 and higher
---------------------

When launching Unity 2019 and higher from ftrack-connect, the Unity Hub will 
appear. There is a limitation with the Unity Hub 2.0 which prevents ftrack from initializing properly. 
You need to stop all running **Unity Hub.exe** processes before launching Unity from 
ftrack-connect. This will be fixed by the Unity team in an upcoming release 
(tentative for Unity Hub 2.1)

Package Manager is not available in Unity
-----------------------------------------

If you cannot see the Package Manager menu item, make sure you installed 
`Microsoft Visual Studio Community <https://learn.unity.com/tutorial/get-started-with-visual-studio-and-unity>`_

Installing `.NET Core prerequisites <http://go.microsoft.com/fwlink/?LinkID=798306&clcid=0x409>`_
might help resolve this problem.
