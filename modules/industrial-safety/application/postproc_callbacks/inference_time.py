import sys
import gi
import json
import time
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from gstgva import VideoFrame

DETECT_THRESHOLD = 0.5

Gst.init(sys.argv)

class InferenceTime:
    """
    Class to add the inference start time to frame messages
    """
    def process_frame(self, frame: VideoFrame):
        """
        method to store the model inference start time

        :param frame: gstgva.VideoFrame object

        :returns bool
        """
        frame.add_message(json.dumps({"time": str(time.time())}))
        return True
