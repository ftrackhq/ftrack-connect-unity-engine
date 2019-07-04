using System.Reflection;
using UnityEditor.Recorder;

namespace UnityEditor.ftrack
{
    public class Recorder
    {
        public static void SetFrameRange(int start, int end)
        {
            var window = EditorWindow.GetWindow<RecorderWindow>(false, "Recorder", false);
            if (!window)
                return;

            // Get the settings through reflection        
            var field = window.GetType().GetField("m_ControllerSettings", BindingFlags.NonPublic | BindingFlags.Instance);
            var settings = field.GetValue(window) as RecorderControllerSettings;
            settings.SetRecordModeToFrameInterval(start, end);

            // Now apply the window settings to all recorders and save the new global settings
            var onGlobalSettingsChanged = window.GetType().GetMethod("OnGlobalSettingsChanged", BindingFlags.NonPublic | BindingFlags.Instance);
            onGlobalSettingsChanged.Invoke(window, new object[]{ });
        }
    }
}
