# Python Installation Validation
To verify that your Python interpreter is properly configured, follow these steps:
* Launch a command prompt/shell
* Type "python"

The Python interpreter should launch. It should report a 64-bit version of Python 2.7

Copy the following code in a Python script (e.g. validate_python.py) and run it, by either:
* using "execfile" in the Python interpreter to execute the script (e.g. `execfile('validate_python.py')`)
* passing the script to the interpreter in a command prompt/shell (e.g. `python.exe validate_python.py`)


*validate_python.py*
```
import sys
# Python version (expected: 2.7 64 bit)
try:
	import platform
	version = platform.python_version()
	tokens = version.split('.')

	if len(tokens) < 2 or int(tokens[0]) != 2 or int(tokens[1]) != 7:
		print('ERROR: invalid Python version. Expected 2.7.x, got %s'%version)
		sys.exit(1)
	
	(bits,_) = platform.architecture()
	if bits != '64bit':
		print('ERROR: invalid architecture. Expected "64bit", got "%s"'%bits)
		sys.exit(1)
	
except:
	print('ERROR: could not determine the Python version')
	sys.exit(1)

# PySide 
try:
	import PySide
except:
	print('ERROR: could not import PySide')
	sys.exit(1)

# rpyc
try:
	import rpyc
except:
	print('ERROR: could not import rpyc')
	sys.exit(1)
	
print('SUCCESS: The Python interpreter is properly configured for using PySide in Unity')
```