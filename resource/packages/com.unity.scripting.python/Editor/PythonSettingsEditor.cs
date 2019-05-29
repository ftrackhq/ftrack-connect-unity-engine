using UnityEngine;
using System.IO;
using Python.Runtime;

namespace UnityEditor.Scripting.Python
{
    internal class PythonSettings : ScriptableObject
    {
        const string PreferencesPath = "ProjectSettings/PythonSettings.asset";

#if UNITY_EDITOR_WIN
        const string kDefaultPython = "python.exe";
#else // linux or mac
        const string kDefaultPython = "python2.7";
#endif

        /// <summary>
        /// Returns the release version.
        ///
        /// Must be made to match the package.json or else things get confusing.
        /// </summary>
        public static string Version
        {
            get { return "1.3.0-preview"; }
        }

        /// <summary>
        /// Returns the Python interpreter we'll be running.
        ///
        /// On an empty string, rely on the system PATH to find Python.
        /// </summary>
        public static string PythonInterpreter
        {
            get
            {
                var pyInterp = instance.m_pythonInterpreter;
                return string.IsNullOrEmpty(pyInterp)
                             ? kDefaultPython : pyInterp;
            }
        }

        [SerializeField]
        internal string m_pythonInterpreter;

        string m_originalPythonInterpreter;

        public static bool PythonInterpreterChanged
        {
            get
            {
                return PythonInterpreter != instance.m_originalPythonInterpreter;
            }
        }

        /// <summary>
        /// Timeout for determining whether a program is Python or something else.
        ///
        /// You'd only want to change this if for some reason your actual Python is sometimes slow to start up.
        /// </summary>
        [SerializeField]
        internal int m_pythonTimeoutMs = 1000;

        /////////
        /// User site-packages.
        /// Set via the serializedObject workflow.
        #pragma warning disable 0649
        [SerializeField]
        internal string [] m_sitePackages;
        #pragma warning restore 0649

        /// <summary>
        /// Set of additional site-packages paths used in your project.
        ///
        /// Example: add your studio scripts here.
        ///
        /// This is a copy; avoid calling SitePackages in a loop.
        /// </summary>
        public static string [] SitePackages
        {
            get
            {
                var sitePackages = instance.m_sitePackages;
                if (sitePackages == null)
                {
                    return new string[0];
                }
                return (string[])sitePackages.Clone();
            }
        }

        /// <summary>
        /// Find an executable on the path.
        ///
        /// If we're looking in the unity virtual file system, look it up there.
        ///
        /// Return an empty string if not found.
        /// </summary>
        public static string WhereIs(string exe)
        {
            if (string.IsNullOrEmpty(exe))
            {
                return exe;
            }

            // On *nix, a path that starts with a ~ is interpreted as being in
            // the home directory. There's no precise equivalent on Windows, so
            // don't support it.
#if !UNITY_EDITOR_WIN
            if (exe[0] == '~')
            {
                var home = System.Environment.GetEnvironmentVariable("HOME");
                if (!string.IsNullOrEmpty(home))
                {
                    exe = home + '/' + exe.Substring(1);
                }
            }
#endif


            // Relative paths not in the current directory need to be interpreted as Unity VFS paths.
            // Absolute paths are absolute already, no need to search the PATH.
            if (exe.IndexOfAny(new char[] { '/', '\\' }) >= 0)
            {
                exe = System.IO.Path.GetFullPath(exe);
                return System.IO.File.Exists(exe) ? exe : "";
            }

            // Use shutil.which -- but that requires Python 3.3 or later.
            // For compatibility, use unity_shutil.which -- the same code copied into our codebase.
            PythonRunner.EnsureInProcessInitialized();
            using(Py.GIL())
            {
                dynamic unity_shutil = PythonEngine.ImportModule("unity_rpyc.unity_shutil");
                dynamic path = unity_shutil.which(exe);
                return path == null ? "" : path.ToString();
            }
        }

        /// <summary>
        /// Validates the Python interpreter.
        ///
        /// Check that it's in the path (or it's a Unity virtual file system path, or an absolute path),
        /// Check that it can run,
        /// Check that it's the right version.
        /// Returns the version.
        ///
        /// With throwErrors, throws a PythonInstallException with a hint of the reason.
        /// Return empty-string if it's not a valid interpreter.
        /// </summary>
        public static string ValidatePythonInterpreter(string pythonRelativePath, bool throwErrors = false)
        {
            try
            {
                if (string.IsNullOrEmpty(pythonRelativePath))
                {
                    throw new PythonInstallException($"Python setting was empty; this should never happen.");
                }

                // pythonRelativePath can be absolute or relative or be in the path.
                // Figure out where it is.
                var python = WhereIs(pythonRelativePath);
                if (string.IsNullOrEmpty(python))
                {
                    throw new PythonInstallException($"{pythonRelativePath} does not seem to be an executable file. Make sure the path is exactly accurate.");
                }

                // Try to run the program. If it's not executable it'll throw.
                // If it's not Python it's unlikely to interpret the arguments as Python code and print 2.7.
                // If it's Python but a broken install, it'll return a bad error code.
                // If it's Python but the wrong version it'll return the wrong version number.
                var py = new System.Diagnostics.Process();
                py.StartInfo.FileName = python;
                // Note: double-quotes required on Windows (single-ticks don't work)
                py.StartInfo.Arguments = "-c \"import sys; print(sys.version)\"";
                py.StartInfo.UseShellExecute = false;
                py.StartInfo.RedirectStandardOutput = true;

                // We need to read stdout asynchronously with the callback in case it's
                // not Python but e.g. Unity -- in which case ReadToEnd would block.
                var output = new System.Text.StringBuilder();
                py.OutputDataReceived += (sender, args) => output.Append(args.Data);
                py.Start();
                py.BeginOutputReadLine();

                // Wait up to 1 second, then kill and wait again to flush stdout.
                if (!py.WaitForExit(instance.m_pythonTimeoutMs))
                {
                    // kill before throwing, or else we get a zombie.
                    py.Kill();
                    throw new PythonInstallException($"{python} took too long to run; either it's not Python, or increase the Python timeout in the Python settings.");
                }

                if (py.ExitCode != 0)
                {
                    throw new PythonInstallException($"{python} acts like it isn't actually Python: it failed with exit code {py.ExitCode}.");
                }

                // If we're here, then we did WaitForExit and succeeded, which means
                // this call should do nothing. But on mono 5.11 at least, if we don't
                // do this, we don't flush stdout:
                py.WaitForExit();

                var pythonVersion = output.ToString().Trim();
                if (!pythonVersion.StartsWith(PythonRunner.PythonRequiredVersion, System.StringComparison.Ordinal))
                {
                    throw new PythonInstallException($"{python} should be version {PythonRunner.PythonRequiredVersion} but instead calls itself {pythonVersion}");
                }

                // If we haven't yet found a reason to reject this Python, it's valid.
                return pythonVersion;
            }
            catch (System.Exception xcp)
            {
                if (throwErrors)
                {
                    // Rethrow if we already have a good error message.
                    if (xcp is PythonInstallException)
                    {
                        throw;
                    }
                    // Throw with an inner exception to provide a better error message.
                    throw new PythonInstallException($"Looking for '{pythonRelativePath}' threw an exception", xcp);
                }
                return "";
            }
        }

        public static string ValidatePythonInterpreter()
        {
            return ValidatePythonInterpreter(PythonInterpreter, throwErrors: true);
        }

        /// <summary>
        /// This class is a singleton. This returns the sole instance, loading
        /// it from the preferences if it hasn't been built yet.
        /// </summary>
        public static PythonSettings instance
        {
            get
            {
                if (s_Instance == null)
                {
                    s_Instance = CreateInstance<PythonSettings>();

                    // Try to load the preferences file. Use defaults otherwise.
                    try
                    {
                        var fileData = System.IO.File.ReadAllText(PreferencesPath);
                        EditorJsonUtility.FromJsonOverwrite(fileData, s_Instance);
                    }
                    catch
                    {
                        s_Instance.m_pythonInterpreter = "";
                    }
                    s_Instance.m_originalPythonInterpreter = PythonInterpreter;
                }
                return s_Instance;
            }
        }
        static PythonSettings s_Instance;

        PythonSettings()
        {
            if (s_Instance != null)
            {
                throw new System.ArgumentException("second instance of PythonSettings being constructed");
            }
        }

        /// <summary>
        /// Save any changes to the preferences file.
        /// </summary>
        internal void Save()
        {
            if (s_Instance == null)
            {
                // Don't save, there's nothing to save.
                return;
            }

            var dirName = Path.GetDirectoryName(PreferencesPath);
            if (!Directory.Exists(dirName))
            {
                Directory.CreateDirectory(dirName);
            }
            File.WriteAllText(PreferencesPath, EditorJsonUtility.ToJson(s_Instance, true));
        }
    }

    [CustomEditor(typeof(PythonSettings))]
    public class PythonSettingsEditor : Editor
    {
        static class Styles
        {
            public static readonly GUIContent pythonInterpreter = new GUIContent("Out-of-process Python", "Location of the Python to use for the out-of-process API");
            public static readonly GUIContent sitePackages = new GUIContent("Site-packages directories", "Directories where your custom scripts are stored. Added to your sys.path ahead of the system sys.path. They are added both to the in-process and out-of-process Python APIs. Relative paths are interpreted within the Unity virtual file system.");
            public static readonly GUIContent testTimeout = new GUIContent("Rarely needed: Timeout (ms) for Python testing", "Timeout in milliseconds to use when testing if the Python interpreter has the right version. Increase this if you're seeing 'took too long to run' errors when you correctly set the out-of-process Python.");
        }

        string m_pythonInterpreterLastSet = null;
        string m_pythonInstallError = "";
        string m_pythonVersionLastSet = null;

        /// <summary>
        /// Sets the Python interpreter if it's valid.
        /// Return the version number if it's valid (empty-string if not).
        /// </summary>
        string SetPythonInterpreter(PythonSettings settings, string pythonInterpreter)
        {
            if (m_pythonInterpreterLastSet == pythonInterpreter)
            {
                return m_pythonVersionLastSet;
            }
            m_pythonInterpreterLastSet = pythonInterpreter;

            string pythonVersion = "";

            // If empty-string, use the system Python no matter if it even exists.
            if (string.IsNullOrEmpty(m_pythonInterpreterLastSet))
            {
                m_pythonInstallError = "";
                settings.m_pythonInterpreter = m_pythonInterpreterLastSet;
                try
                {
                    pythonVersion = PythonSettings.ValidatePythonInterpreter();
                }
                catch (PythonInstallException xcp)
                {
                    m_pythonInstallError = xcp.Message;
                    Debug.LogException(xcp);
                }
            }
            else
            {
                try
                {
                    pythonVersion = PythonSettings.ValidatePythonInterpreter(m_pythonInterpreterLastSet, throwErrors: true);
                    m_pythonInstallError = "";
                    settings.m_pythonInterpreter = m_pythonInterpreterLastSet;
                }
                catch (PythonInstallException xcp)
                {
                    m_pythonInstallError = xcp.Message;
                    Debug.LogException(xcp);
                }
            }
            m_pythonVersionLastSet = pythonVersion;
            return pythonVersion;
        }

        static string ShortPythonVersion(string longPythonVersion)
        {
            // The long Python version is e.g.
            //  2.7.16 |Anaconda, Inc.| (default, Mar 14 2019, 16:24:02) \n[GCC 4.2.1 Compatible Clang 4.0.1 (tags/RELEASE_401/final)]
            // The short Python version for that is '2.7.16'
            //
            // Return the long Python version if it doesn't parse as a short version.
            if (string.IsNullOrEmpty(longPythonVersion))
            {
                return "";
            }

            var firstSpace = longPythonVersion.IndexOf(' ');
            if (firstSpace < 0)
            {
                return longPythonVersion;
            }
            return longPythonVersion.Substring(0, firstSpace);
        }

        public override void OnInspectorGUI()
        {
            try
            {
                OnInspectorGUICanThrow();
            }
            catch (System.Exception xcp)
            {
                Debug.LogException(xcp);
            }
            if (GUI.changed) {
                var settings = (PythonSettings)target;
                EditorUtility.SetDirty(settings);
                settings.Save();
            }
        }

        /// <summary>
        /// Draw the editor UI in immediate mode.
        ///
        /// Called by OnInspectorGUI, which catches any exception we throw here.
        /// </summary>
        void OnInspectorGUICanThrow()
        {
            // Overall UI layout for now: information at the top.
            // Settings for in-process next (may also affect out-of-process Python).
            // Settings for out-of-process next.
            // TODO: nicer UI.

            var settings = (PythonSettings)target;

            // TODO: label + selectable label so users can copy-paste package version
            // (and the same for all versions below)
            EditorGUILayout.LabelField("Python for Unity. Package Version: " + PythonSettings.Version);

            EditorGUILayout.Separator();

            EditorGUILayout.LabelField(
                new GUIContent("In-process Python Version " + ShortPythonVersion(PythonRunner.InProcessPythonVersion),
                               "The Python for the in-process API is determined by the path when you started Unity. Currently it is version:\n"
                               + PythonRunner.InProcessPythonVersion));

            // End of the info section. Start of the in-process section.
            EditorGUILayout.Separator();

            // The site packages array goes through the serializedObject code path
            // to offer the usual array modification workflow in the UI.
            // TODO: make this much prettier.
            var sitePackagesArray = serializedObject.FindProperty("m_sitePackages");
            EditorGUI.BeginChangeCheck();
            EditorGUILayout.PropertyField(sitePackagesArray, Styles.sitePackages, true);
            if (EditorGUI.EndChangeCheck())
            {
                serializedObject.ApplyModifiedProperties();
            }

            // End of the in-process section; start of the out-of-process section.
            EditorGUILayout.Separator();

            // TODO: add a '...' button to pop up a file dialog instead of typing.
            if (m_pythonInterpreterLastSet == null)
            {
                SetPythonInterpreter(settings, PythonSettings.PythonInterpreter);
            }
            var pythonInterpreter = EditorGUILayout.DelayedTextField(Styles.pythonInterpreter, m_pythonInterpreterLastSet);
            var pythonVersion = SetPythonInterpreter(settings, pythonInterpreter.Trim());
            if (!string.IsNullOrEmpty(m_pythonInstallError))
            {
                EditorGUILayout.HelpBox(m_pythonInstallError, MessageType.Error);
            }
            else
            {
                EditorGUILayout.LabelField(
                    new GUIContent("Out-of-process Python Version: " + ShortPythonVersion(pythonVersion),
                                   "The Python for the out-of-process API is determined by the setting above. Currently it is version:\n"
                                   + pythonVersion));
            }

            if (PythonSettings.PythonInterpreterChanged)
            {
                EditorGUILayout.HelpBox("Restart Unity to use the new Python", MessageType.Warning);
            }

            EditorGUILayout.Separator();
            settings.m_pythonTimeoutMs = EditorGUILayout.DelayedIntField(Styles.testTimeout, settings.m_pythonTimeoutMs);
        }

        [SettingsProvider]
        static SettingsProvider CreatePythonSettingsProvider()
        {
            return new AssetSettingsProvider("Project/Python", () => PythonSettings.instance);
        }
    }
}
