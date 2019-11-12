..
    :copyright: Copyright (c) 2019 ftrack

.. _install:


Install
=======

Python
------

Install `Python 2.7.15 (64 bits) or later <https://www.python.org/downloads/release/python-2716/>`_.

.. warning::
    The package does not work with Python 3.

Once python is installed, from a cmd prompt, type `python` and make sure the installed Python can be
discovered. If not, adjust your **%PATH%** environment variable to include the path
where Python.exe resides.

In the Python interpreter, type the following code and make sure the returned value matches the directory where you installed Python:

.. code::

    >>> import sys
    >>> print sys.executable

Quit the interpreter by typing

.. code::

    >>> quit()

Git
---

In order for Unity to pull packages from remote git repositories, the git application should be 
available. Please refer to your operating system application store to locate and install it.


install
=======

Whether you have been downloading the integration or built yourself, 
copy the uncompressed folder in the **%FTRACK_CONNECT_PLUGIN_PATH%**

You can find more information on how to locate it in the `ftrack help page <https://help.ftrack.com/connect/getting-started-with-connect/installing-and-using-connect>`_