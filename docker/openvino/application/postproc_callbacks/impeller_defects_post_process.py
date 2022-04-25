import sys
import gi
import json
import time
import io
import numpy as np
import base64
from opcua import Client
import paho.mqtt.client as mqtt
import shap
import cv2
import matplotlib.pyplot as plt
from tensorflow.keras.models import Sequential, load_model
import os


gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
from gstgva import VideoFrame

DETECT_THRESHOLD = 0.5

Gst.init(sys.argv)

class DefectDetection:
    """Defect detection """
    def __init__(self) -> None:
        self.initialize_defectdetection()
        self.client = self.connect_opcua()
        self.mqtt_client = self.connect_mqtt()

    def connect_mqtt(self) -> mqtt.Client:
        """
        Connect to MQTT broker

        :returns mqtt.Client
        """
        mqtt_client = mqtt.Client()
        mqtt_client.connect("mosquittoserver", 1883, 60)
        return mqtt_client

    def connect_opcua(self):
        """Connect to opcua server

        :returns client: opcua client object
        """
        opcua_url = "opc.tcp://opcuaserver:4840"
        client = Client(opcua_url)
        client.connect()

        return client

    def set_opcua_values(self, violation: int, accuracy: float, fps: float) -> None:
        """Set inference results to opcua variables

        :param weld_class: Weld Class detected
        :param prob: Probabilty of the class detected
        :param fps: Frame per second of the model

        :returns None
        """
        # get variables
        defect_detections = self.client.get_node("ns=2;i=4")
        defect_accuracy = self.client.get_node("ns=2;i=5")
        defect_fps = self.client.get_node("ns=2;i=6")

        # set values to the variables
        defect_detections.set_value(violation)
        defect_accuracy.set_value(accuracy)
        defect_fps.set_value(fps)

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

    def initialize_defectdetection(self):
        resources_path= "/application/resources/"
        train_path = resources_path + "train/"
        tf_model_path = "/application/models/impeller-defect-custom/hdf5/casting_product_detection.hdf5"
        self.model = load_model(tf_model_path)
        self.image_shape = (300,300,1)
        train_cases = ['ok_front/'+i for i in os.listdir(train_path + 'ok_front')]
        train_cases.extend(['def_front/'+i for i in os.listdir(train_path + 'def_front')])
        train_sample = [cv2.imread(train_path + i,
                                   cv2.IMREAD_GRAYSCALE).reshape(1, *self.image_shape) / 255
                        for i in np.random.choice(train_cases, 3000, replace=False)]
        self.explainer = shap.DeepExplainer(self.model, train_sample[0])

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
        with frame.data() as mat:
            current_frame = mat.copy()
            grayed = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)\
                         .reshape(1, *self.image_shape) / 255
            self.infer_explain_frame(grayed, frame, fps)
        return True

    def infer_explain_frame(self, image, frame, fps):
        image = image.reshape(1, *self.image_shape)
        prediction = self.model.predict(image)
        predicted_label = None
        prob = None
        defects = 0
        if (prediction < 0.5):
            predicted_label = "Defective"
            prob = (1-prediction.sum()) * 100
            defects = 1
        else:
            predicted_label = "OK"
            prob = prediction.sum() * 100

        shap_values = self.explainer.shap_values(image)
        shap.image_plot(shap_values, image, show=False)
        buf = io.BytesIO()
        plt.title('Impeller is {} \n Probability is {:.3f} %'.format(predicted_label, prob), weight='bold', size=12)
        plt.axis('off')

        plt.savefig(buf, format='jpg')
        buf.seek(0)
        file_bytes = np.asarray(bytearray(buf.read()), dtype=np.uint8)
        image_cv = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        infer_metadata = {
            "stream": "defectdetection",
            "impeller_status": predicted_label,
            "accuracy": prob,
            "defects": defects,
            "target" : self.get_target_hardware(),
            "fps" : fps,
            "image": self.encode_frame(image_cv)
        }
        self.set_opcua_values(defects, prob, fps)
        plt.close()
        self.mqtt_client.publish("defectdetection", json.dumps(infer_metadata))
        return buf