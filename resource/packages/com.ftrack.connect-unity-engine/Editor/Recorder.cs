using System.Reflection;
using UnityEditor.Recorder;

namespace UnityEditor.ftrack
{
    public class Recorder
    {
        public static void ApplySettings(int start, int end, float fps)
        {
            var window = EditorWindow.GetWindow<RecorderWindow>(false, "Recorder", false);
            if (!window)
                return;

            // Get the settings through reflection        
            var field = window.GetType().GetField("m_ControllerSettings", BindingFlags.NonPublic | BindingFlags.Instance);
            var settings = field.GetValue(window) as RecorderControllerSettings;
            settings.SetRecordModeToFrameInterval(start, end);
            
            // Get the dictionary of frame rate options to float values
            var frameRateDictField = settings.GetType().GetField("s_FPSToValue", BindingFlags.NonPublic | BindingFlags.Static);
            var frameRateDict = frameRateDictField.GetValue(null) as System.Collections.IDictionary;

            // Get the frame rate type field to set with the appropriate enum value
            var frameRateTypeField = settings.GetType().GetField("m_FrameRateType", BindingFlags.NonPublic | BindingFlags.Instance);

            bool setValue = false;
            foreach (System.Collections.DictionaryEntry keyValuePair in frameRateDict)
            {
                float fpsRounded = (float)System.Math.Round(fps, 2);
                float value = (float)System.Math.Round((float)keyValuePair.Value, 2);
                if(fpsRounded == value)
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

            // Now apply the window settings to all recorders and save the new global settings
            var onGlobalSettingsChanged = window.GetType().GetMethod("OnGlobalSettingsChanged", BindingFlags.NonPublic | BindingFlags.Instance);
            onGlobalSettingsChanged.Invoke(window, new object[]{ });
        }
    }
}
