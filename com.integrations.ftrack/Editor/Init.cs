﻿// Copyright (c) 2019 ftrack

using UnityEngine;
using UnityEditor.Scripting.Python;

namespace UnityEditor.Integrations.ftrack
{
    public static class Init
    {
        [InitializeOnLoadMethod]
        private static void InitFtrack()
        {
            string resourcePath = System.Environment.GetEnvironmentVariable("FTRACK_UNITY_RESOURCE_PATH");
            if (null == resourcePath)
            {
                Debug.LogError("FTRACK_UNITY_RESOURCE_PATH was not found in the environment. Make sure to launch Unity from ftrack-connect to use the ftrack integration");
                return;
            }

            // ftrack runs in the client process. This Python script is 
            // responsible to control ftrack (open dialogs, init, …)
            string initModule = System.IO.Path.Combine(resourcePath, "scripts", "ftrack_client_init.py");

            PythonRunner.StartServer(initModule);
            PythonRunner.CallServiceOnClient("'ftrack_load_and_init'");
        }

        [MenuItem("ftrack/Info")]
        private static void ShowInfoDialog()
        {
            PythonRunner.CallServiceOnClient("'ftrack_show_dialog'", "'Info'");
        }
    }
}