..
    :copyright: Copyright (c) 2019 ftrack

.. _trubleshooting:


Trubleshooting
==============

Known issues and Limitations
----------------------------

* The ftrack plug-in for Unity is currently supported on Windows platforms.


Locating Unity installations
----------------------------

If selecting a task does not make the Unity logo appear, you can try to set the 
**%UNITY_LOCATION%** environment variable to point to a valid Unity.exe editor. 
Otherwise the following notes from the Unity hook should help you make sure your 
editors can be discovered:

If **%UNITY_LOCATION%** is specified in the environment, it will be the only 
listed editor. Otherwise we discover Unity installations using these 
locations:

.. note::

    The registry 
    **%HKEY_CURRENT_USER%\Software\Unity Technologies\Installer**.

    This includes all the versions of Unity that were installed using the Hub

.. note::

    **%APPDATA%\UnityHub\editors.json**

   This includes all the installations that were added using the 
   "Locate a version" option in the Unity Hub

.. note::

    **%APPDATA%\UnityHub\secondaryInstallPath.json**

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

SSL Errors
----------
If an SSL error is present during the run of the plugin please ensure OpenSSL for windows is installed and the full path to the libraries

* libeay32.dll
* sleay32.dll

are added in the %PATH%


Can publish only image sequence
--------------------------------

The current integration allows to publish only image_sequence asset types.
Due to technical limitations we are not able at the moment to disable the publish for the other asset types, 
but we are actively looking into a solution.

Result Image Sequence frames are vertically flipped
----------------------------------------------------

In case the image sequence is vertically flipped, change the recording settings for Capture to TargetCamera and set Flip Vertical.