import sys
import gi
import json
import time
import base64
from opcua import Client
import paho.mqtt.client as mqtt
import cv2
from tensorflow.keras.models import Sequential, load_model
import os
from tf_explain.core.grad_cam import GradCAM
import tensorflow as tf

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
        tf_model_path = "/application/models/impeller-defect-custom/hdf5/casting_product_detection.hdf5"
        self.model = load_model(tf_model_path)
        self.image_shape = (300,300,1)

        self.gradcam_explainer = GradCAM()

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
            grayed = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY) \
                         .reshape(1, *self.image_shape) / 255
            self.infer_explain_frame_with_gradcam(grayed, current_frame, fps)
        return True

    def infer_explain_frame_with_gradcam(self, image, frame, fps):

        image = image.reshape(1, *self.image_shape)
        prediction = self.model.predict(image)
        predicted_label = None
        prob = None
        defects = 0
        font_color = (0, 0, 0)
        background_color = (98, 252, 3)

        if (prediction < 0.5):
            predicted_label = "Defective"
            prob = (1-prediction.sum()) * 100
            defects = 1
            background_color = (0, 0, 255)
        else:
            predicted_label = "OK"
            prob = prediction.sum() * 100

        explainer_temp_image_path = "/application/resources/ktrain.jpg"
        cv2.imwrite(explainer_temp_image_path, frame)

        cv2.rectangle(frame, (2, 2), (150, 25), background_color, -1)
        cv2.putText(frame, predicted_label + ":" + "{:.1f}".format(prob) + "%", (5, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, font_color, 1, cv2.LINE_AA)
        frame = frame.reshape((300,300,4))
        img_pil = tf.keras.preprocessing.image.load_img(explainer_temp_image_path, target_size=(300,300), color_mode='grayscale')
        img_array = tf.keras.preprocessing.image.img_to_array(img_pil)
        image_data = ([img_array], None)
        image_cv = self.gradcam_explainer.explain(image_data, self.model, class_index=0)
        image_cv = image_cv.reshape(300,300,3)
        infer_metadata = {
            "stream": "defectdetection",
            "impeller_status": predicted_label,
            "accuracy": prob,
            "defects": defects,
            "target" : self.get_target_hardware(),
            "fps" : fps,
            "explainedimage": self.encode_frame(image_cv),
            "image": self.encode_frame(frame)
        }
        self.set_opcua_values(defects, prob, fps)
        self.mqtt_client.publish("defectdetection", json.dumps(infer_metadata))