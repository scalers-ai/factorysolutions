import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from gstgva import VideoFrame

DETECT_THRESHOLD = 0.5

Gst.init(sys.argv)

def process_frame(frame: VideoFrame):
    for tensor in frame.tensors():
        prediction = tensor.data()[0]
        if prediction < 0:
            continue
        if prediction == 1.0:
            frame.add_region(75, 75, 0, 0, "OK", 100)
        else:
            frame.add_region(75, 75, 0, 0, "Defective", 100)
    return True