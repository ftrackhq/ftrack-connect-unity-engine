# Installation Requirements

* [Python 2.7.5 (64 bits) or later](https://www.python.org/downloads/release/python-2716/). The package does not work with Python 3.

* [Unity 2018.3](https://unity3d.com/get-unity/download). We recommend installing the latest version of Unity 2018 via the Unity Hub; 2018.3 is the minimum. Unity 2019 is not yet fully tested.

* Projects must use the [.NET 4.x Equivalent](https://docs.unity3d.com/Manual/ScriptingRuntimeUpgrade.html) scripting runtime version. This is the default for new projects but needs to be changed by hand when importing projects from earlier versions of Unity.

* Optional: To run the [PySide example](pysideExampleWalkthrough.html), you will need the [PySide](https://wiki.qt.io/PySide) package.

## Windows

Install the software listed above in the default locations.

To get PySide after installing Python, open a command terminal and run:
```
pip install pyside
```

## Mac

Install the Unity Hub and Unity in the default location.

### System Python
For the in-process API, and for out-of-process with RPyC alone but not PySide, the system Python is sufficient.

### Python with PySide
For the out-of-process API with PySide, installation is more complicated because [PySide](https://stackoverflow.com/questions/41472350/installing-pyside-on-mac-is-there-a-working-method) support is lacking. There are a few workarounds.

The key goal:
* Within Unity, go to `Edit -> Project Settings -> Python` and set the `Out of process Python` to point to a Python that includes PySide support.
* Verify installation by [running the PySide example](pysideExampleWalkthrough.html).

There are many options to get PySide installed and visible from Unity. Two that we have tested include:

#### Install macports Python

* Install [MacPorts](https://macports.org)

* Install Python and PySide by pasting in the Terminal:
```
sudo port install python27 py27-pyside
```

* Within Unity, go to `Edit -> Project Settings -> Python` and set the out of process Python setting  to read
```
/opt/local/bin/python2.7
```
* Restart Unity.
* Verify installation by [running the PySide example](pysideExampleWalkthrough.html).

#### Use Shotgun's Python

* Install Autodesk's Shotgun Desktop app
* Within Unity, go to `Edit -> Project Settings -> Python` and set the out of process Python setting  to read
```
/Applications/Shotgun.app/Contents/Resources/Python/bin/python
```
* Restart Unity.
* Verify installation by [running the PySide example](pysideExampleWalkthrough.html).
