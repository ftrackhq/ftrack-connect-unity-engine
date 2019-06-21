using UnityEngine;
using System.Reflection;
using UnityEditor.Recorder;

namespace UnityEditor.ftrack.recorder
{
    public class Recorder
    {
        public static RecorderControllerSettings GetRecorderControllerSettings(RecorderWindow recorderWindow)
        {
            FieldInfo field = recorderWindow.GetType().GetField("m_ControllerSettings", BindingFlags.NonPublic | BindingFlags.Instance);
            return field.GetValue(recorderWindow) as RecorderControllerSettings;
        }
    }
}
