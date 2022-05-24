import sys
import gi
import json
import time
import yaml
import cv2
import numpy as np
import base64
import os
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
from opcua import Client


gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from gstgva import VideoFrame

DETECT_THRESHOLD = 0.5

Gst.init(sys.argv)

class TripWire:
    """Trip wire detection """
    def __init__(self) -> None:
        self.initialize_tripwire()
        self.client = self.connect_opcua()

    def connect_opcua(self):
        """Connect to opcua server

        :returns client: opcua client object
        """
        opcua_url = "opc.tcp://opcuaserver:4840"
        client = Client(opcua_url)
        client.connect()

        return client

    def set_opcua_values(self, violation: int, fps: int) -> None:
        """Set inference results to opcua variables

        :param weld_class: Weld Class detected
        :param prob: Probabilty of the class detected
        :param fps: Frame per second of the model

        :returns None
        """
        # get variables
        safety_violation = self.client.get_node("ns=2;i=2")
        safety_fps = self.client.get_node("ns=2;i=3")
        safety_target_hardware = self.client.get_node("ns=2;i=4")

        # set values to the variables
        safety_violation.set_value(violation)
        safety_fps.set_value(fps)
        if self.get_target_hardware() == 'CPU':
            safety_target_hardware.set_value(0.0)
        else:
            safety_target_hardware.set_value(1.0)

    def get_target_hardware(self):
        """Read target hardware of the pipeline from
        TARGET environment variable
        """
        try:
            target = os.environ['DEFECT_TARGET_HARDWARE']
        except Exception:
            target = 'CPU'

        return target

    def encode_frame(self, image) -> str:
        """Encode the frame after reshaping

        :param image: np.ndarray

        :return : str
        """
        #TODO remove this hardcoding.
        width = 770
        height = 434
        resized_image = cv2.resize(
            image, (width, height),
            interpolation=cv2.INTER_AREA
        )
        _, buffer = cv2.imencode('.jpg', resized_image)
        return base64.b64encode(buffer).decode()


    # load the yaml file for the coordinates.
    def initialize_tripwire(self):
        with open("/application/data/tripwire_coordinates.yml", "r") as data:
            # initialize trip wire polygon from yml file.
            self.TRIPWIRE_COORDS = yaml.safe_load(data)

    """
    Class to handle trip wire violation detections and image processing
    """
    def process_frame(self, frame: VideoFrame):
        """
        method to handle tripwire logic

        :param frame: gstgva.VideoFrame object

        :returns bool
        """
        # calculate FPS
        data = json.loads(frame.messages()[0])['time']
        inference_time = time.time() - float(data)
        fps = 1 / inference_time
        for message in frame.messages():
            frame.remove_message(message)
        # generate encoded image with tripwire detections.
        violations = 0
        with frame.data() as mat:
            current_frame = mat.copy()
            color = (0, 255, 0)
            thickness = 2
            for id, tripwire in enumerate(self.TRIPWIRE_COORDS):
                pts = np.array(tripwire['coordinates'], np.int32)
                polygon = Polygon(tripwire['coordinates'])
                persons = []
                for roi in frame.regions():
                    rect = roi.rect()
                    persons.append([rect.x, rect.y, rect.x + rect.w, rect.y + rect.h])
                    for person in persons:
                        p1 = ((person[2]-person[0])/2)+person[0]
                        point1 = Point((p1, person[3]))
                        # color to change based on whether there is a bounding box inside the polygon.
                        # red if tripwire tripped else green
                        inside_tripwire = polygon.contains(point1)
                        if inside_tripwire:
                            violations = 1
                            color = (0, 0, 255)
                        else:
                            color = (0, 255, 0)
                        cv2.circle(current_frame, (int(p1), person[3]), 10, color, -1)
                cv2.polylines(current_frame, [pts],
                    True, color, thickness)
                infer_metadata = {
                    "stream": "industrialsafety",
                    "person_count": len(persons),
                    "violations": violations,
                    "fps": fps,
                    "image": self.encode_frame(current_frame),
                    "target" : self.get_target_hardware()
                }
                self.set_opcua_values(violations, fps)
                frame.add_message(json.dumps(infer_metadata))
        return True
