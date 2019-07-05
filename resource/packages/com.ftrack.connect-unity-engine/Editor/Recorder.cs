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
            
            //////////// TODO ////////////////
            /// Use the mapping algorithm discussed on Slack
            /// Set the FramerateType to the right enum, or set a value 
            /// It will switch the FramerateType to CUSTOM if I am correct.
            /// (see RecorderControllerSettings.cs)
            settings.frameRate = fps;
            //////////// TODO ////////////////

            // Now apply the window settings to all recorders and save the new global settings
            var onGlobalSettingsChanged = window.GetType().GetMethod("OnGlobalSettingsChanged", BindingFlags.NonPublic | BindingFlags.Instance);
            onGlobalSettingsChanged.Invoke(window, new object[]{ });
        }
    }
}
