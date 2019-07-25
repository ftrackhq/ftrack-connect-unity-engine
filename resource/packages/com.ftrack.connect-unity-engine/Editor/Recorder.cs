using System.Reflection;
using UnityEditor.Recorder;
using System.Collections;
using UnityEditor.Scripting.Python;

namespace UnityEditor.ftrack
{
    public class ImageSequenceRecorder : FtrackRecorder<ImageRecorderSettings> {
        /// <summary>
        /// We must install the delegate on each domain reload
        /// </summary>
        [InitializeOnLoadMethod]
        private static void OnReload()
        {
            if (IsRecording)
            {
                EditorApplication.playModeStateChanged += OnPlayModeStateChange;
            }
            s_filename = "frame.<Frame>";
        }
    }

    public class MovieRecorder : FtrackRecorder<MovieRecorderSettings> {
        /// <summary>
        /// We must install the delegate on each domain reload
        /// </summary>
        [InitializeOnLoadMethod]
        private static void OnReload()
        {
            if (IsRecording)
            {
                EditorApplication.playModeStateChanged += OnPlayModeStateChange;
            }
            s_filename = "reviewable";
        }
    }

    public class FtrackRecorder<T> where T : RecorderSettings
    {
        private static string s_origFilePath = null;
        private static RecorderSettings s_recorderSettings = null;
        protected static string s_filename = "test";

        public static void Record()
        {
            IsRecording = true;

            s_origFilePath = RecorderPath;

            RecorderPath = GetTempFilePath();

            // Delete the temp folder if it already exists
            string folderPath = System.IO.Directory.GetParent(RecorderPath.Replace('<', '_').Replace('>', '_')).FullName;
            if (System.IO.Directory.Exists(folderPath))
            {
                System.IO.Directory.Delete(folderPath, true);
            }

            EditorApplication.playModeStateChanged += OnPlayModeStateChange;

            StartRecording();
        }

        private static string lockFilePath = GetTempFolderPath() + ".RecordTimeline.lock";
        protected static bool IsRecording
        {
            get
            {
                return System.IO.File.Exists(lockFilePath);
            }
            set
            {
                if (value == true)
                {
                    System.IO.File.Create(lockFilePath);
                }
                else
                {
                    if (System.IO.File.Exists(lockFilePath))
                    {
                        System.IO.File.Delete(lockFilePath);
                    }
                }
            }
        }

        /// <summary>
        /// Returns a deterministic path based on the project name
        /// e.g. %TEMP%\Unity_Project_Name for the Windows platform
        /// </summary>
        /// <returns>The path</returns>
        private static string GetTempFilePath()
        {
            // store to a temporary path, to delete after publish
            var tempPath = System.IO.Path.GetTempPath();

            // TODO: what should the name of the video file be?
            tempPath = System.IO.Path.Combine(tempPath, UnityEngine.Application.productName);

            return tempPath + "/" + s_filename;
        }

        private static string GetTempFolderPath()
        {
            // store to a temporary path, to delete after publish
            var tempPath = System.IO.Path.GetTempPath();

            // TODO: what should the name of the video file be?
            tempPath = System.IO.Path.Combine(tempPath, UnityEngine.Application.productName);

            return tempPath;
        }

        protected static void OnPlayModeStateChange(PlayModeStateChange state)
        {
            if (IsRecording)
            {
                // Domain reloads lose the overriden Recorder path. We know a 
                // domain reload occurred if m_origFilePath is not set (cleared 
                // by a domain reload)
                if (null == s_origFilePath)
                {
                    s_origFilePath = RecorderPath;
                    RecorderPath = GetTempFilePath();
                }

                if (state == PlayModeStateChange.EnteredEditMode)
                {
                    // Publish with ftrack
                    PythonRunner.CallServiceOnClient("'publish_callback'", string.Format("'{0}'", RecorderPath));

                    EditorApplication.playModeStateChanged -= OnPlayModeStateChange;
                    RecorderPath = s_origFilePath;
                    IsRecording = false;
                }
            }
        }

        private static object GetFieldValue(string fieldName, object from)
        {
            FieldInfo fi = from.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);
            return fi.GetValue(from);
        }

        private static object GetPropertyValue(string propName, object from, BindingFlags bindingFlags = BindingFlags.NonPublic | BindingFlags.Instance)
        {
            PropertyInfo propInfo = from.GetType().GetProperty(propName, bindingFlags);
            return propInfo.GetValue(from);
        }

        private static RecorderSettings RecorderSettings
        {
            get
            {
                if (s_recorderSettings == null)
                {
                    s_recorderSettings = GetRecorder();
                    if (s_recorderSettings == null)
                    {
                        UnityEngine.Debug.LogError("Could not find a valid MovieRecorder");
                    }
                }
                return s_recorderSettings;
            }
        }

        private static string RecorderPath
        {
            get { return RecorderSettings.outputFile; }
            set
            {
                RecorderSettings.outputFile = value;
            }
        }

        private static void StartRecording()
        {
            var recorderWindow = EditorWindow.GetWindow<RecorderWindow>();
            if (!recorderWindow)
            {
                return;
            }
            // start recording
            recorderWindow.StartRecording();
        }

        private static RecorderSettings GetRecorder()
        {
            var recorderWindow = EditorWindow.GetWindow<RecorderWindow>();
            if (!recorderWindow)
            {
                return null;
            }

            // first try to get the selected item, if it's not a MovieRecorder,
            // then go through the list and try to find one that is called "ftrack".
            // if there isn't one then just take one of the MovieRecorders.
            var selectedRecorder = GetFieldValue("m_SelectedRecorderItem", recorderWindow);
            if (selectedRecorder != null)
            {
                RecorderSettings recorderSettings = GetPropertyValue("settings", selectedRecorder, BindingFlags.Public | BindingFlags.Instance) as RecorderSettings;
                if (recorderSettings.GetType().Equals(typeof(T)))
                {
                    // found movie recorder settings
                    return recorderSettings as T;
                }
            }

            var recorderList = GetFieldValue("m_RecordingListItem", recorderWindow);
            var itemList = (IEnumerable)GetPropertyValue("items", recorderList, BindingFlags.Public | BindingFlags.Instance);
            T movieRecorder = null;
            foreach (var item in itemList)
            {
                RecorderSettings settings = GetPropertyValue("settings", item, BindingFlags.Public | BindingFlags.Instance) as RecorderSettings;
                var recorder = settings as T;
                if (recorder == null)
                {
                    continue;
                }
                movieRecorder = recorder;

                var editableLabel = GetFieldValue("m_EditableLabel", item);
                var labelText = (string)GetPropertyValue("text", editableLabel);
                if (labelText.Equals("ftrack"))
                {
                    return movieRecorder;
                }
            }
            return movieRecorder;
        }

        public static void ApplySettings(int start, int end, float fps)
        {
            var window = EditorWindow.GetWindow<RecorderWindow>(
                false,"Recorder", false
            );
            if (!window)
                return;

            // Get the settings through reflection        
            var field = window.GetType().GetField("m_ControllerSettings",
                BindingFlags.NonPublic | BindingFlags.Instance);

            var settings = field.GetValue(window) as RecorderControllerSettings;
            settings.SetRecordModeToFrameInterval(start, end);
            
            // Get the dictionary of frame rate options to float values
            var frameRateDictField = settings.GetType().GetField("s_FPSToValue",
                BindingFlags.NonPublic | BindingFlags.Static);

            var frameRateDict = frameRateDictField.GetValue(null) 
                as System.Collections.IDictionary;

            // Get the frame rate type field to set with 
            // the appropriate enum value
            var frameRateTypeField = settings.GetType().GetField(
                "m_FrameRateType",
                BindingFlags.NonPublic | BindingFlags.Instance
            );

            bool setValue = false;
            foreach (DictionaryEntry keyValuePair in frameRateDict)
            {
                float value = (float)keyValuePair.Value;
                if(UnityEngine.Mathf.Abs(fps - value) < 0.01f)
                {
                    frameRateTypeField.SetValue(settings, keyValuePair.Key);
                    setValue = true;
                    break;
                }
            }

            if (!setValue)
            {
                settings.frameRate = fps;
            }

            // Now apply the window settings to all recorders 
            // and save the new global settings
            var onGlobalSettingsChanged = window.GetType().GetMethod(
                "OnGlobalSettingsChanged",
                BindingFlags.NonPublic | BindingFlags.Instance
            );
            onGlobalSettingsChanged.Invoke(window, new object[]{ });
        }
    }
}
