# :coding: utf-8
# :copyright: Copyright (c) 2019 ftrack

# ftrack
from distutils.version import LooseVersion

import ftrack
import ftrack_connect.application

# misc
import getpass
import json
import logging
import os
import pprint
import sys

_cwd = os.path.dirname(__file__)
_sources_path = os.path.abspath(os.path.join(_cwd, '..', 'dependencies'))

if _sources_path not in sys.path:
    sys.path.append(_sources_path)

import ftrack_connect_unity

class LaunchApplicationAction(object):
    identifier = 'ftrack-connect-launch-unity'
    def __init__(self, application_store, launcher):
        super(LaunchApplicationAction, self).__init__()

        self.logger = logging.getLogger(__name__ + '.' + self.__class__.__name__)
        self.application_store = application_store
        self.launcher = launcher

    def is_valid_selection(self, selection):
        """
        Unity needs a task to operate
        """
        if (len(selection) != 1 or selection[0]['entityType'] != 'task'):
            return False

        entity = selection[0]
        task = ftrack.Task(entity['entityId'])

        if task.getObjectType() != 'Task':
            return False

        return True

    def register(self):
        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.action.discover and source.user.username={0}'.format(getpass.getuser()),
            self.discover)
        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.action.launch and source.user.username={0} and data.actionIdentifier={1}'.format(getpass.getuser(), self.identifier),
            self.launch)

        ftrack.EVENT_HUB.subscribe(
            'topic=ftrack.connect.plugin.debug-information',
            self.get_version_information
        )

    def discover(self, event):
        '''
        Return discovered applications.
        
        Note: there are mismatches about the dict layouts we use here and what 
        is documented online for the discover event
        
        https://help.ftrack.com/developing-with-ftrack/key-concepts/events
        
        The event layout and the returned items dict layout are different.
        What we use here is based on the Maya hook 
        '''
        if not self.is_valid_selection(event['data'].get('selection', [])):
            return

        items = []
        applications = self.application_store.applications

        for application in applications:
            items.append(
                {
                'label': application['label'],
                'icon': application.get('icon', 'default'),
                'variant': application.get('variant', None),
                'actionIdentifier': self.identifier,
                'applicationIdentifier': application['identifier'],
                'description': unicode(application['description'])
                }
            )

        return { 'items': items }

    def launch(self, event):
        '''
        Launches a specific Unity version

        Note: there is a mismatch about the event dict layout we use here and 
        what is documented online for the launch event
        
        https://help.ftrack.com/developing-with-ftrack/key-concepts/events
        
        What we use here is based on the Maya hook 
        '''
        # Prevent further processing by other listeners.
        event.stop()

        if not self.is_valid_selection(event['data'].get('selection', [])):
            return

        context = event['data'].copy()
        context['source'] = event['source']

        application_identifier = event['data']['applicationIdentifier']

        return self.launcher.launch(application_identifier, context)

    def get_version_information(self, event):
        return dict(
            name='ftrack connect unity',
            version=ftrack_connect_unity.__version__
        )


class ApplicationStore(ftrack_connect.application.ApplicationStore):

    def _discoverApplications(self):
        all_applications = []

        if sys.platform == 'win32':
            """
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
               
            We make sure there are no duplicates.
            We make sure the executable files exist.
            We use %APPDATA%\UnityHub\defaultEditor.json to determine the default 
            editor. If we find the default editor we make it the first item of the 
            list. 
            """
            # Using the environment variable overrides the discovery and 
            # only offers one specific version of Unity
            # The version is unknown is that case
            unity_location_override = os.environ.get('UNITY_LOCATION')
            if unity_location_override and os.path.exists(unity_location_override):
                all_applications.append( 
                    {
                    'description': 'Launch Unity ({})'.format(unity_location_override),
                    'icon': 'https://cdn4.iconfinder.com/data/icons/various-icons-2/476/Unity.png',
                    'identifier': 'unity_unknown',
                    'label': 'Unity',
                    'launchArguments': None,
                    'path': unity_location_override,
                    'variant': 'Unknown',
                    'version': LooseVersion ('Unknown'),
                    }
                )
            else:
                self._discover_from_registry(all_applications)
                self._discover_located_editors(all_applications)
                self._discover_secondary_installations(all_applications)
                self._discover_standard_paths(all_applications)

        elif 'linux' in sys.platform:
            prefix = os.environ['HOME'].split(os.path.sep)[1:]
            prefix.insert(0, '/')
            prefix.extend(['Unity', 'Hub', 'Editor', '2.+'])
            print 'prefix', prefix
            all_applications.extend(self._searchFilesystem(
                expression=prefix + ['Editor', 'Unity$'],
                versionExpression=r'(?P<version>\d[\d.a-z]*?)[^\d]*$',
                label='Unity',
                applicationIdentifier='unity_{version}',
                icon='unity',
                variant='{version}'
            ))

        print all_applications

        # Remove:
        #   * paths that do not exist 
        #   * duplicate paths
        #   * duplicate versions
        valid_applications = []
        valid_paths = []
        valid_versions = []
        for application in all_applications:
            path = application['path']
            version = application['variant']
            
            if not os.path.exists(path):
                # The executable does not exist. Skip
                continue
            
            if path in valid_paths:
                # We already have this editor. Skip
                continue
            
            if version in valid_versions:
                # We already have this version. Skip
                continue
            
            # We found a new valid application
            valid_applications.append(application)
            valid_paths.append(path)
            valid_versions.append(version)
        
        # Sort the list
        valid_applications = sorted(valid_applications, key=lambda application: application['variant'])
        
        if sys.platform == 'win32':
            # Try to find the preferred version and make it the first version of the
            # list
            # %APPDATA%\UnityHub\defaultEditor.json
            json_file = os.path.join(os.environ.get('APPDATA'), 'UnityHub', 'defaultEditor.json')
            if os.path.exists(json_file):
                with open(json_file, "r") as f:
                    preferred_version = json.load(f)
    
                    # We are expecting a single string which is the version number 
                    # for the preferred editor
                    if type(preferred_version) == unicode:
                        for application in valid_applications:
                            if application['variant'] == preferred_version:
                                valid_applications.remove(application)
                                valid_applications.insert(0, application)

        self.logger.debug('Discovered Unity applications:\n{0}'.format(pprint.pformat(valid_applications)))
        return valid_applications
    
    def _discover_from_registry(self, applications):
        if sys.platform != 'win32':
            # Discovering through the registry is specific to the Windows 
            # platform
            return 

        try:
            import _winreg
            with _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\Unity Technologies\Installer') as installer_hkey:
                # One sub_key per installation
                (installer_nb_sub_keys, _, __) = _winreg.QueryInfoKey(installer_hkey)
                
                for installer_sub_key_index in range(installer_nb_sub_keys):
                    installer_sub_key_name = _winreg.EnumKey(installer_hkey, installer_sub_key_index)
                    
                    # Open the sub_key
                    with _winreg.OpenKey(installer_hkey, installer_sub_key_name) as editor_hkey:
                        # One sub_key per installation
                        editor_path = None
                        editor_version = None
                        
                        (_, editor_nb_values, __) = _winreg.QueryInfoKey(editor_hkey)
                        for editor_value_index in range(editor_nb_values):
                            (editor_value_name, editor_value, _) = _winreg.EnumValue(editor_hkey, editor_value_index)
                            if editor_value_name == 'Location x64':
                                editor_path = editor_value
                            elif editor_value_name == 'Version':
                                editor_version = editor_value

                        if editor_path and editor_version:
                            # Valid candidate, add it to the list
                            path = os.path.join(editor_path,'Editor','Unity.exe')
                            applications.append( 
                                {
                                'description': 'Launch Unity {} ({})'.format(editor_version, path),
                                'icon': 'https://cdn4.iconfinder.com/data/icons/various-icons-2/476/Unity.png',
                                'identifier': 'unity_{}'.format(editor_version),
                                'label': 'Unity',
                                'launchArguments': None,
                                'path': path,
                                'variant': editor_version,
                                'version': LooseVersion(editor_version),
                                }
                            )
        except Exception as e:
            self.logger.debug('Exception raised while accessing the registry (HKEY_CURRENT_USER\Software\Unity Technologies\Installer): {}'.format(e))
    
    def _discover_located_editors(self, applications):
        json_file = None
        if sys.platform == 'win32':
            # %APPDATA%\UnityHub\editors.json
            json_file = os.path.join(os.environ.get('APPDATA'), 'UnityHub', 'editors.json')
            
        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                data = json.load(f)
                if not data or type(data) != dict:
                    return

                for entry in data.values():
                    version = entry.get('version')
                    if not version:
                        continue
                    
                    locations = entry.get('location')
                    if not locations:
                        continue
                    
                    # Use the first one
                    unity_location = locations[0]
                    applications.append( 
                        {
                        'description': 'Launch Unity {} ({})'.format(version, unity_location),
                        'icon': 'https://cdn4.iconfinder.com/data/icons/various-icons-2/476/Unity.png',
                        'identifier': 'unity_{}'.format(version),
                        'label': 'Unity',
                        'launchArguments': None,
                        'path': unity_location,
                        'variant': version,
                        'version': LooseVersion(version),
                        }
                    )
        
    def _discover_from_location(self, expression_to_search, applications):
        """
        Will discover installations under the given expression
        expression is a list of string tokens
            e.g. [ 'C:', 'Program Files', 'Unity' ]
        """
        expression_to_search.extend(['2.+', 'Editor', 'Unity.exe'])
        found_applications = self._searchFilesystem(
            expression = expression_to_search,
            versionExpression = r'(?P<version>\d[\d.a-z]*?)[^\d]*$',
            label='Unity',
            applicationIdentifier='unity_{version}',
            icon='https://cdn4.iconfinder.com/data/icons/various-icons-2/476/Unity.png',
            variant='{version}'
        )
        
        # Set a description on found applications
        for application in found_applications:
            application['description'] = 'Launch Unity {} ({})'.format(application['variant'], application['path']),
        
        applications.extend(found_applications)
        

    def _discover_secondary_installations(self, applications):
        json_file = None
        if sys.platform == 'win32':
            # %APPDATA%\UnityHub\secondaryInstallPath.json
            json_file = os.path.join(os.environ.get('APPDATA'), 'UnityHub', 'secondaryInstallPath.json')

        if os.path.exists(json_file):
            with open(json_file, "r") as f:
                data = json.load(f)

                # We are expecting a single string which is the root 
                # location to scan
                if type(data) == unicode:
                    # Feed the file system search algorithm with the 
                    # discovered root. We expect the Unity version to be
                    # its own folder, e.g. D:\my_path\2018.3.12f1\Editor\Unity.exe
                    #
                    # The first part of the expression must match exactly to an 
                    # existing entry on the filesystem
                    expression = data.split(os.sep)
                    if not expression or len(expression) < 1:
                        return

                    if not os.path.exists(expression[0]):
                        return
                    
                    self._discover_from_location(expression, applications)

    def _discover_standard_paths(self, applications):
        """
        Searches standard locations
        """
        expressions_to_search = None
        if sys.platform == 'win32':
            expressions_to_search = [ ['C:', 'Program Files', 'Unity', 'Hub', 'Editor'] ] 

        for expression in expressions_to_search:
            if os.path.exists(os.path.sep.join(expression)):
                self._discover_from_location(expression, applications)


class ApplicationLauncher(ftrack_connect.application.ApplicationLauncher):
    def __init__(self, application_store):
        super(ApplicationLauncher, self).__init__(application_store)

    def _getApplicationEnvironment(self, application, context=None):
        # Make sure to call super to retrieve original environment
        # which contains the selection and ftrack API.
        environment = super(ApplicationLauncher, self)._getApplicationEnvironment(application, context)
        
        # We need the dependencies in sys.path
        ftrack_connect.application.appendPath(
           _sources_path,
            'PYTHONPATH',
            environment
        )
        
        # Make sure the plug-in is in sys.path
        ftrack_connect.application.appendPath(
            os.path.join(_sources_path, 'ftrack_connect_unity'),
            'PYTHONPATH',
            environment
        )

        environment['FTRACK_UNITY_RESOURCE_PATH'] = os.path.abspath(os.path.join(_cwd, '..', 'resources'))
        
        entity = context['selection'][0]
        task = ftrack.Task(entity['entityId'])
        taskParent = task.getParent()

        try:
            environment['FS'] = str(int(taskParent.getFrameStart()))
        except Exception:
            environment['FS'] = '0'

        try:
            environment['FE'] = str(int(taskParent.getFrameEnd()))
        except Exception:
            environment['FE'] = '0'
        
        environment['FTRACK_TASKID'] = task.getId()
        environment['FTRACK_SHOTID'] = task.get('parent_id')

        ftrack_installation_path = os.path.dirname(sys.executable)

        environment = ftrack_connect.application.appendPath(
            ftrack_installation_path,
            'QT_PLUGIN_PATH',
            environment
        )

        environment = ftrack_connect.application.appendPath(
            ftrack_installation_path,
            'PYTHONPATH',
            environment
        )

        environment = ftrack_connect.application.appendPath(
            os.path.join(ftrack_installation_path, "library.zip"),
            'PYTHONPATH',
            environment
        )

        return environment

def register(registry, **kw):
    # Validate that registry is the event handler registry. If not,
    # assume that register is being called to register Locations or from a new
    # or incompatible API, and return without doing anything.
    if registry is not ftrack.EVENT_HANDLERS:
        return

    # Create store containing applications.
    application_store = ApplicationStore()

    # Create a launcher with the store containing applications.
    launcher = ApplicationLauncher(application_store)
    
    # Create action and register to respond to discover and launch actions.
    action = LaunchApplicationAction(application_store, launcher)
    action.register()
    