# Changes in Python.Net

RELEASE NOTES
## [1.3.0-preview] - 2019-04-24

NEW FEATURES
* Updated documentation
* Add Python project settings in Unity
* Improved support for installing on Mac and Linux
* Improved logging to help troubleshooting
* Include rpyc and dependencies in Package
* Add option to use different Python on client

## [1.2.0-preview] - 2019-03-13

NEW FEATURES
* Automatically adding Python/site-packages to the PYTHONPATH for the current project and the Python packages
* Added ability to log the Python client messages into a file
* More robust reconnection on domain reload

## [1.1.4-preview] - 2018-12-21

NEW FEATURES
* Added a sample: PySideExample
* Added documentation for In-Process and Out-of-Process APIs
* Better exception logging on the client when an exception is raised on init
* Better error messages when the Python installation is not valid
* RPyC client now automatically starts on server start

## [1.1.3-preview] - 2018-12-14

NEW FEATURES
- This version provides tidier assemblies and APIs

## [1.1.2-preview] - 2018-12-07
NEW FEATURES
- Added a Python example using the rpyc architecture and PySide in the client process
- The rpyc client process now terminates when Unity exits
- The rpyc client can now be stopped and restarted
- Better logging of Python exceptions in the Unity console
- Improved error message when the Python interpreter is not properly configured
- Added a Python/Debug menu that allows to
- - Start the rpyc server
- - Stop the rpyc server
- - Start the rpyc client
- - Start the rpyc server and the client

## [1.1.1-preview] - 2018-11-26

NEW FEATURES
- Added methods to PythonRunner for 
  - Running Python on the rpyc client
  - Starting and stopping the rpyc server
  - Preventing .pyc files from being generated

FIXES
- Fixed deadlocks when closing the rpyc server and client

## [1.1.0-preview] - 2018-11-13

NEW FEATURES
- Added rpyc architecture (under Python/site-packages/unity_rpyc)
- Updated Python .NET to include:
  - A fix to a crash when finalizing the Python interpreter on domain unload
  - A C# callback on Python .NET shutdown

KNOWN ISSUES
- There might be scenarios that still crash/hang Unity when running Python after reloading assemblies. 
  - If your tools are affected by domain reload, consider using the rpyc architecture. Refer to the documentation for an example on how to use the rpyc architecture.

## [1.0.0] - 2018-10-05

NEW FEATURES
- added Python support in Unity for Windows and Mac
