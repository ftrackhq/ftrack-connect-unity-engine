# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

import os
import re
import shutil
import sys


from setuptools.command.test import test as TestCommand
from setuptools import setup, find_packages, Command
from pkg_resources import parse_version
import subprocess

# Define paths

PLUGIN_NAME = 'ftrack-connect-unity-engine-{0}'
ROOT_PATH = os.path.dirname(os.path.realpath(__file__))

SOURCE_PATH = os.path.join(ROOT_PATH, 'source')
README_PATH = os.path.join(ROOT_PATH, 'README.rst')
BUILD_PATH = os.path.join(ROOT_PATH, 'build')
RESOURCE_PATH = os.path.join(ROOT_PATH, 'resource')
SCRIPTS_PATH = os.path.join(RESOURCE_PATH, 'scripts')
HOOK_PATH = os.path.join(RESOURCE_PATH, 'hook')

STAGING_PATH = os.path.join(BUILD_PATH, PLUGIN_NAME)

# Parse package version
with open(os.path.join(SOURCE_PATH, 'ftrack_connect_unity', '_version.py')) as _version_file:
    VERSION = re.match(r'.*__version__ = \'(.*?)\'', _version_file.read(), re.DOTALL).group(1)

# Update staging path with the plugin version
STAGING_PATH = STAGING_PATH.format(VERSION)

# Custom commands.
class BuildPlugin(Command):
    '''Build plugin.'''

    description = 'Download dependencies and build plugin .'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        '''Run the build step.'''
        # Clean staging path
        shutil.rmtree(STAGING_PATH, ignore_errors=True)

        # Copy hook files
        shutil.copytree(
            HOOK_PATH,
            os.path.join(STAGING_PATH, 'hook')
        )
        
        # Copy script files
        shutil.copytree(
            SCRIPTS_PATH,
            os.path.join(STAGING_PATH, 'resource', 'scripts')
        )
        
        # Copy readme file
        shutil.copyfile(README_PATH, os.path.join(STAGING_PATH, 'README.md'))

        # Install local dependencies
        subprocess.check_call(
            [sys.executable, '-m', 'pip', 'install','.','--target',
            os.path.join(STAGING_PATH, 'dependencies')]
        )


        # Generate plugin zip
        shutil.make_archive(
            os.path.join(
                BUILD_PATH,
                PLUGIN_NAME.format(VERSION)
            ),
            'zip',
            STAGING_PATH
        )


# Configuration.
setup(
    name='ftrack connect Unity engine',
    version=VERSION,
    description='ftrack integration for Unity.',
    long_description=open(README_PATH).read(),
    keywords='',
    url='https://bitbucket.org/ftrack/ftrack-connect-unity-engine/',
    author='ftrack',
    author_email='support@ftrack.com',
    license='Apache License (2.0)',
    packages=find_packages(SOURCE_PATH),
    package_dir={
        '': 'source'
    },
    setup_requires=[
        'sphinx >= 1.8.5',
        'sphinx_rtd_theme >= 0.1.6, < 2',
        'lowdown >= 0.1.0, < 1'
    ],
    tests_require=[
        'pytest >= 2.3.5, < 3'
    ],
    cmdclass={
        'build_plugin': BuildPlugin,
    },
    install_requires=[
        'appdirs',
        'ftrack-connector-legacy @ git+https://bitbucket.org/ftrack/ftrack-connector-legacy/get/1.0.0.zip#egg=ftrack-connector-legacy-1.0.0',
        'qtext @ git+https://bitbucket.org/ftrack/qtext/get/0.2.2.zip#egg=QtExt-0.2.2',
        'Qt.py == 0.3.4',
        'PySide'
    ],
    python_requires=">=2.7.9, <3"
)
