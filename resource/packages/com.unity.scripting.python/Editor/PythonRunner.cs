using UnityEditor;
using UnityEngine;
using Python.Runtime;
using System;
using System.IO;
using System.Collections.Generic;

namespace UnityEditor.Scripting.Python
{
    /// <summary>
    /// Exception thrown when Python is installed incorrectly so we can't
    /// run.
    /// </summary>
    public class PythonInstallException : System.Exception
    {
        public PythonInstallException() : base() { }
        public PythonInstallException(string msg) : base(msg) { }
        public PythonInstallException(string msg, Exception innerException) : base(msg, innerException) { }
        protected PythonInstallException(System.Runtime.Serialization.SerializationInfo info,
            System.Runtime.Serialization.StreamingContext context) : base(info, context) { }

        public override string Message => $"Python Net: {base.Message}\nPlease check the Python Net package documentation for the install troubleshooting instructions.";
    }

    public static class PythonRunner
    {
        const string ImportServerString = "from unity_rpyc import unity_server as unity_server\n";

        /// <summary>
        /// The Python version we require.
        ///
        /// Changing this to 3 isn't going to magically make it work, the constant is just to help find some parts that matter.
        /// </summary>
        public const string PythonRequiredVersion = "2.7";

        public static string InProcessPythonVersion
        {
            get
            {
                using (Py.GIL())
                {
                    dynamic sys = PythonEngine.ImportModule("sys");
                    return sys.version.ToString();
                }
            }
        }

        /// <summary>
        /// Runs Python code in the Unity process
        /// </summary>
        /// <param name="pythonCodeToExecute">The code to execute.</param>
        public static void RunString(string pythonCodeToExecute)
        {
            EnsureInProcessInitialized();
            using (Py.GIL ())
            {
                try
                {
                    PythonEngine.Exec(pythonCodeToExecute);
                }
                catch (PythonException e)
                {
                    string msg = e.ToString();
                    string stacktrace = e.StackTrace.Replace("\\n", "\n");
                    Debug.LogError($"{msg}\npython stack: {stacktrace}");
                    throw;
                }
            }
        }

        /// <summary>
        /// Runs a Python script in the Unity process
        /// </summary>
        /// <param name="pythonFileToExecute">The script to execute.</param>
        public static void RunFile(string pythonFileToExecute)
        {
            EnsureInProcessInitialized();
            if (null == pythonFileToExecute)
            {
                throw new System.ArgumentNullException("pythonFileToExecute", "Invalid (null) file path");
            }

            // Forward slashes please
            pythonFileToExecute = pythonFileToExecute.Replace("\\","/");
            if (!File.Exists (pythonFileToExecute))
            {
                throw new System.IO.FileNotFoundException("No Python file found at " + pythonFileToExecute, pythonFileToExecute);
            }

            using (Py.GIL ())
            {
                try
                {
                    PythonEngine.Exec(string.Format("execfile('{0}')", pythonFileToExecute));
                }
                catch (PythonException e)
                {
                    string msg = e.ToString();
                    string stacktrace = e.StackTrace.Replace("\\n", "\n");
                    Debug.LogError($"{msg}\npython stack: {stacktrace}");
                    throw;
                }
            }
        }

        /// <summary>
        /// Starts the Unity server (rpyc)
        /// </summary>
        /// <param name="clientInitModulePath">Optional path to the client init module that should be used when the Unity client starts.</param>
        public static void StartServer(string clientInitModulePath = null)
        {
            EnsureOutOfProcessInitialized();

            string clientInitPathString;
            if (clientInitModulePath != null)
            {
                clientInitModulePath = clientInitModulePath.Replace("\\","/");
                clientInitPathString = string.Format("'{0}'",clientInitModulePath);
            }
            else
            {
                clientInitPathString = "None";
            }

            // Start the server. Might throw.
            // TODO: run this with dynamic variables instead of a RunString, to
            // avoid needing to quote clientInitPathString.
            string serverCode = $"{ImportServerString}\n" +
                $"unity_server.start({clientInitPathString})\n";
            RunString(serverCode);

            // We need to stop the server on Python shutdown
            // (which is triggered by domain unload)
            PythonEngine.AddShutdownHandler(OnPythonShutdown);
        }

        /// <summary>
        /// Stops the Unity server
        /// </summary>
        /// <param name="terminateClient">Also terminates the client process. Default is false</param>
        public static void StopServer(bool terminateClient = false)
        {
            EnsureOutOfProcessInitialized();
            // TODO: run this with dynamic variables
            string serverCode = ImportServerString + string.Format(@"unity_server.stop({0})", terminateClient ? "True" : "False");
            RunString(serverCode);
        }

        /// <summary>
        /// Runs Python code on the Python client
        /// </summary>
        /// <param name="pythonCodeToExecute">The code to execute.</param>
        public static void RunStringOnClient(string pythonCodeToExecute)
        {
            EnsureOutOfProcessInitialized();
            using (Py.GIL())
            {
                try
                {
                    dynamic unity_server = PythonEngine.ImportModule("unity_rpyc.unity_server");
                    unity_server.run_python_code_on_client(pythonCodeToExecute);
                }
                catch (PythonException e)
                {
                    string msg = e.ToString();
                    string stacktrace = e.StackTrace.Replace("\\n", "\n");
                    Debug.LogError($"{msg}\npython stack: {stacktrace}");
                    throw;
                }
            }
        }

        /// <summary>
        /// Runs a Python script on the Python client
        /// </summary>
        /// <param name="pythonFileToExecute">The script to execute.</param>
        public static void RunFileOnClient(string pythonFileToExecute)
        {
            EnsureOutOfProcessInitialized();

            if (null == pythonFileToExecute)
            {
                throw new System.ArgumentNullException("pythonFileToExecute", "Invalid (null) file path");
            }

            // Forward slashes please
            pythonFileToExecute = pythonFileToExecute.Replace("\\","/");

            if (!File.Exists (pythonFileToExecute))
            {
                throw new System.IO.FileNotFoundException("No Python file found at " + pythonFileToExecute, pythonFileToExecute);
            }

            // TODO: run this as dynamic variables so we don't need to quote the filename
            string serverCode = ImportServerString + string.Format(@"unity_server.run_python_file_on_client('{0}')",pythonFileToExecute);
            RunString(serverCode);
        }

        /// <summary>
        /// Calls a rpyc service method on the client (remote call)
        /// </summary>
        /// <param name="serviceName">The name of the service.</param>
        /// <param name="pythonArgs">The Python args passed to the service as a string.</param>
        public static void CallServiceOnClient(string serviceName, string pythonArgs = "None")
        {
            EnsureOutOfProcessInitialized();
            // TODO: run this as dynamic variables so we don't need to quote the arguments
            string serverCode = ImportServerString + string.Format(@"unity_server.call_remote_service({0},{1})",serviceName,pythonArgs);
            RunString(serverCode);
        }

        /// <summary>
        /// Stops the Unity server when Python shuts down
        /// </summary>
        private static void OnPythonShutdown()
        {
            StopServer();
            PythonEngine.RemoveShutdownHandler(OnPythonShutdown);
        }

        /// <summary>
        /// Ensures the in-process Python API is initialized.
        ///
        /// Safe to call frequently.
        ///
        /// Throws if there's an installation error.
        /// </summary>
        public static void EnsureInProcessInitialized()
        {
            if (s_IsInProcessInitialized)
            {
                return;
            }
            DoEnsureInProcessInitialized();
            s_IsInProcessInitialized = true;
        }
        static bool s_IsInProcessInitialized = false;

        /// <summary>
        /// This is a helper for EnsureInProcessInitialized; call that function instead.
        ///
        /// This function assumes the API hasn't been initialized, and does the work of initializing it.
        /// </summary>
        static void DoEnsureInProcessInitialized()
        {
            ///////////////////////
            // Tell the Python interpreted not to generate .pyc files. Packages
            // are installed in read-only locations on some OSes and if package
            // developers forget to remove their .pyc files it could become
            // problematic. This can be changed at runtime by a script.
            System.Environment.SetEnvironmentVariable("PYTHONDONTWRITEBYTECODE", "1");

            ///////////////////////
            // Initialize the engine if it hasn't been initialized yet.
            PythonEngine.Initialize();

            // Verify that we are running the right version of Python.
            if (!PythonEngine.Version.Trim().StartsWith(PythonRequiredVersion, StringComparison.Ordinal))
            {
                throw new PythonInstallException($"Python {PythonRequiredVersion} is required but your system Python is {PythonEngine.Version}.");
            }

            ///////////////////////
            // Add the packages we use to the sys.path, and put them at the head.
            // TODO: remove duplicates.
            using (Py.GIL())
            {
                // Get the builtin module, which is 'builtins' on python3 and __builtin__ on python2
                dynamic builtins = PythonEngine.ImportModule("__builtin__");

                // prepend to sys.path
                dynamic sys = PythonEngine.ImportModule("sys");
                dynamic syspath = sys.GetAttr("path");
                dynamic sitePackages = GetExtraSitePackages();
                dynamic pySitePackages = builtins.list();
                foreach(var sitePackage in sitePackages)
                {
                    pySitePackages.append(sitePackage);
                }
                pySitePackages += syspath;
                sys.SetAttr("path", pySitePackages);

                // Log what we did. TODO: just to the editor log, not the console.
                Debug.Log("sys.path = " + sys.GetAttr("path").ToString());
            }
        }

        /// <summary>
        /// Returns a list of the extra site-packages that we need to prepend to sys.path.
        ///
        /// These are absolute paths.
        /// </summary>
        static List<string> GetExtraSitePackages()
        {
            // The site-packages that contains rpyc need to be first. Others, we don't
            // have a well-reasoned order.
            var sitePackages = new List<string>();

            // 1. Our package's Python/site-packages directory. This needs to be first.
            {
                string packageSitePackage = Path.GetFullPath("Packages/com.unity.scripting.python/Python/site-packages");
                packageSitePackage = packageSitePackage.Replace("\\", "/");
                sitePackages.Add(packageSitePackage);
            }

            // 2. The present project's Python/site-packages directory, if it exists.
            if (Directory.Exists("Assets/Python/site-packages"))
            {
                var projectSitePackages = Path.GetFullPath("Assets/Python/site-packages");
                projectSitePackages = projectSitePackages.Replace("\\", "/");
                sitePackages.Add(projectSitePackages);
            }

            // 3. TODO: Do we want to iterate over the Package Manager to add their Python/site-packages?
            //    For now, we don't. But we might want to revisit that for later.

            // 4. The packages from the settings.
            foreach(var settingsPackage in PythonSettings.SitePackages)
            {
                var settingsSitePackage = Path.GetFullPath(settingsPackage);
                settingsSitePackage = settingsSitePackage.Replace("\\", "/");
                sitePackages.Add(settingsSitePackage);
            }

            return sitePackages;
        }

        /// <summary>
        /// Ensures the out of process API is initialized.
        ///
        /// Safe to call frequently.
        ///
        /// Throws if there's an installation error.
        /// </summary>
        public static void EnsureOutOfProcessInitialized()
        {
            if (s_IsOutOfProcessInitialized)
            {
                return;
            }
            DoEnsureOutOfProcessInitialized();
            s_IsOutOfProcessInitialized = true;
        }
        static bool s_IsOutOfProcessInitialized = false;

        /// <summary>
        /// Helper for EnsureOutOfProcessInitialized; call that function instead.
        ///
        /// This function assumes the API hasn't been initialized, and does the work of initializing it.
        /// </summary>
        static void DoEnsureOutOfProcessInitialized()
        {
            // We need Python in-process to run the out-of-process API.
            EnsureInProcessInitialized();

            // TODO: support per-client preferences.
            // Validate that the Python we're going to run actually works.
            if (string.IsNullOrEmpty(PythonSettings.ValidatePythonInterpreter()))
            {
                throw new PythonInstallException($"Check the Python Settings and verify the Python Interpreter points to a valid Python {PythonRequiredVersion} installation.\nPython Interpreter is currently '{PythonSettings.PythonInterpreter}'");
            }

            // We need rpyc on the Unity (server) side.
            // TODO: grab it from pip if we don't have it.
            using (Py.GIL())
            {
                var rpyc = PythonEngine.ImportModule("rpyc");
                if (!rpyc.IsTrue())
                {
                    // TODO: we could just run python -m pip install --target Library/site-packages rpyc
                    // Then add that directory to the sys.path
                    throw new PythonInstallException($"Install rpyc where the system Python can find it.");
                }
            }

            // Set the server settings. We do this by setting globals in unity_server.
            using (Py.GIL())
            {
                // Get the builtin module, which is 'builtins' on python3 and __builtin__ on python2
                dynamic builtins = PythonEngine.ImportModule("__builtin__");

                var unity_server = PythonEngine.ImportModule("unity_rpyc.unity_server");
                var clientPython = PythonSettings.WhereIs(PythonSettings.PythonInterpreter);
                unity_server.SetAttr("python_executable", new PyString(clientPython));
                var extraSitePackages = builtins.list();
                foreach(var sitePackage in GetExtraSitePackages())
                {
                    extraSitePackages.append(new PyString(sitePackage));
                }
                unity_server.SetAttr("extra_site_packages", extraSitePackages);

                // TODO: we need a way to tell the client, too!
                // unity_server.SetAttr("polling_port", new PyInt(PythonSettings.instance.m_pollingPort));
                // unity_server.SetAttr("client_port", new PyInt(PythonSettings.instance.m_clientPort));
            }

            // Verify the spawned Python can find rpyc. If it can't, the client would die silently, unable to connect.
            // Best to discover that here and raise an exception already.
            bool clientFoundRpyc = false;
            try
            {
                // get the builtin module, which is 'builtins' on python3 and __builtin__ on python2
                dynamic builtins = PythonEngine.ImportModule("__builtin__");

                // retval = unity_rpyc.unity_server.UnityServer.spawn_subpython(["-c", "import rpyc"]).wait()
                dynamic unity_server = PythonEngine.ImportModule("unity_rpyc.unity_server");
                dynamic UnityServer = unity_server.UnityServer;
                dynamic args = builtins.list();
                args.append(new PyString("-c"));
                args.append(new PyString("import rpyc"));
                dynamic sub = UnityServer.spawn_subpython(args, logging: false);
                if (sub == null)
                {
                    // Failing due to rpyc missing is one thing, but not even
                    // running means something worse is happening. Make it log.
                    UnityServer.spawn_subpython(args, logging: true);
                    throw new PythonInstallException($"Check the prior log; unable to run client Python '{PythonSettings.PythonInterpreter}'.");
                }
                else
                {
                    dynamic retval = sub.wait();
                    if (!retval.IsTrue())
                    {
                        // 0 is false, but 0 is success
                        clientFoundRpyc = true;
                    }
                }
            }
            catch(Exception xcp)
            {
                if (xcp is PythonInstallException)
                {
                    throw;
                }
                throw new PythonInstallException($"Check your Python Net settings; unable to run client Python '{PythonSettings.PythonInterpreter}'.", xcp);
            }
            if (!clientFoundRpyc)
            {
                // TODO: we could just run python -m pip install --target Library/site-packages rpyc
                // Then add that directory to the PYTHONPATH when running Python.
                throw new PythonInstallException($"Please install rpyc in {PythonSettings.PythonInterpreter}");
            }

            // TOTAL SUCCESS!
            // We want to stop the client and server on application exit
            EditorApplication.quitting += OnQuit;
        }

        private static void OnQuit()
        {
            StopServer(true);
            EditorApplication.quitting -= OnQuit;
        }

    #if DEBUG
        [MenuItem("Python/Debug/Start rpyc server (and client)")]
        private static void DebugStartServer()
        {
            StartServer();
        }

        [MenuItem("Python/Debug/Stop rpyc server")]
        private static void DebugStopServer()
        {
            StopServer();
        }

        [MenuItem("Python/Debug/Stop rpyc server and client")]
        private static void DebugStopServerAndClient()
        {
            StopServer(true);
        }
    #endif
    }
}
