..
    :copyright: Copyright (c) 2019 ftrack

.. _use:


Use
===

Setting up a Unity project
--------------------------

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

1. Make sure you have Git installed. You can download it from [here](https://git-scm.com/download/win)
1. In the Package Manager window, locate the `+` sign, click on it, then 
select `Add package from git URL...`
1. Enter the following URL: `https://bitbucket.org/ftrack/ftrack-connect-unity-plugin.git`

ftrack should initialize and a menu named `ftrack` should be available in Unity

Note: ftrack dialogs tend to show behind the Unity editor window.