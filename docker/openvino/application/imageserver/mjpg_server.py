import cv2
import numpy as np
import argparse
from flask import Flask, render_template, Response
import logging as log
import paho.mqtt.client as mqtt
import json
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WritePrecision
import time
import base64
import urllib.request
from flask import flash, request, redirect, url_for
from flask import send_from_directory

ap = argparse.ArgumentParser()

ap.add_argument("-m", "--model", required=True,
                help="path to hdf5 model")
ap.add_argument("-inflxh", "--influxdbhost", required=True,
                help="InfluxDb host name")
ap.add_argument("-inflxp", "--influxdbport", required=True,
                help="InfluxDb port name")
ap.add_argument("-f", "--safetyfeedname", required=True,
                help="The mqtt topic to listen to")
ap.add_argument("-d", "--defectfeedname", required=True,
                help="The mqtt topic to listen to")
ap.add_argument("-mq", "--mqtthost", required=True,
                help="The mqtt host name")
ap.add_argument("-o", "--organization", required=True,
                help="The org. against which influx data is logged")
ap.add_argument("-t", "--token", required=True,
                help="The influx token to read/ write data")
ap.add_argument("-b", "--bucket", required=True,
                help="The influx bucket to read/ write data")
ap.add_argument("-cf", "--tripwire_coordinates_file", required=True,
                help="The coordinates for the trip wire.")

args = vars(ap.parse_args())

IPADDRESS = args['influxdbhost']
INFLUXDBPORT = args['influxdbport']
INFLUXBUCKET = args['bucket']
INPUTFEED_NAME = args['safetyfeedname']
DEFECTFEED_NAME = args['defectfeedname']
INFLUX_API_TOKEN=args['token']
INFLUX_ORG=args['organization']
MQTT_HOST = args['mqtthost']
HFD5_MODEL_PATH=args['model']
MQTT_CLIENT_NAME =   INPUTFEED_NAME + "-mqttclient2"
COORDINATES_FILE = args['tripwire_coordinates_file']
trip_wire_image = None
impeller_defect_image = None
impeller_explained_image = None

explainer = None
model = None
image_shape = (300,300,1)
resources_path='/application/resources/'
inside_tripwire = False
client = None
db_client = None
write_api = None

# Create object for Flask class
app = Flask(__name__, template_folder=resources_path)
log_ = log.getLogger('werkzeug')

TRIPWIRE_COORDS = None

def on_disconnect(client, userdata,rc=0):
    log.debug("DisConnected result code "+str(rc))
    client.loop_stop()

def on_message(client, userdata, message):
    process_stream(message.payload.decode("utf-8"))

def init_model_explainer():
    global client
    global db_client
    global write_api

    # Init mqtt client
    client = mqtt.Client(MQTT_CLIENT_NAME) #create new instance
    client.connect(MQTT_HOST) #connect to broker
    log.debug("Subscribing to topic",INPUTFEED_NAME)
    client.subscribe(INPUTFEED_NAME)
    client.subscribe(DEFECTFEED_NAME)
    client.ondisconnect = on_disconnect
    client.on_message=on_message

    # Init influx client
    db_client = InfluxDBClient(url="http://{}:{}".format(IPADDRESS, INFLUXDBPORT), token=INFLUX_API_TOKEN, org=INFLUX_ORG)
    write_api = db_client.write_api(write_options=ASYNCHRONOUS)


def generate_explainer_image():
    global impeller_explained_image
    while True:
        time.sleep(0.01)
        ret, impeller_explained_image_encoded = cv2.imencode('.jpg', impeller_explained_image)
        if ret:
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + impeller_explained_image_encoded.tobytes() + b'\r\n')
        else:
            empty_image = generate_empty_image()
            cv2.putText(img=empty_image, text='No Data', org=(150, 250), fontFace=cv2.FONT_HERSHEY_TRIPLEX,
                        fontScale=3, color=(0, 255, 0),thickness=3)
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + empty_image.tobytes() + b'\r\n')

def generate():
    global impeller_defect_image
    while True:
        time.sleep(0.01)
        ret, impeller_defect_image_encoded = cv2.imencode('.jpg', impeller_defect_image)
        if ret:
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + impeller_defect_image_encoded.tobytes() + b'\r\n')
        else:
            empty_image = generate_empty_image()
            cv2.putText(img=empty_image, text='No Data', org=(150, 250), fontFace=cv2.FONT_HERSHEY_TRIPLEX,
                        fontScale=3, color=(0, 255, 0),thickness=3)
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + empty_image.tobytes() + b'\r\n')

def generate_safety_feed():
    global trip_wire_image
    while True:
        time.sleep(0.01)
        ret, trip_wire_image_encoded = cv2.imencode('.jpg', trip_wire_image)
        if ret:
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + trip_wire_image_encoded.tobytes() + b'\r\n')
        else:
            empty_image = generate_empty_image()
            cv2.putText(img=empty_image, text='No Data', org=(150, 250), fontFace=cv2.FONT_HERSHEY_TRIPLEX,
                        fontScale=3, color=(0, 255, 0),thickness=3)
            yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + empty_image.tobytes() + b'\r\n')

def generate_empty_image():
    return np.ones(shape=(300,300,1), dtype=np.int16)

@app.route('/impeller_conveyor')
def impeller_conveyor():
    return send_from_directory('static', 'impeller_conveyor.mp4')

@app.route('/explainmodel')
def impeller_quality_video_feed():
    """
    Trigger the explainmodel() function on opening "0.0.0.0:5000/explainmodel" URL
    :return: image with explanation and inference details
    """
    return Response(generate_explainer_image(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/currentmodel')
def impeller_quality_video_feed_current():
    """
    Trigger the explainmodel() function on opening "0.0.0.0:5000/explainmodel" URL
    :return: image with explanation and inference details
    """
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/industrialsafety')
def safety_video_feed():
    """
    Trigger the safety_video_feed() function on opening "0.0.0.0:5000/industrialsafety" URL
    :return: image with detections and tripwire overlays.
    """
    return Response(generate_safety_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')


def decode(encoded_img: str) -> np.ndarray:
    """
    Decode base64 encoded images received over mqtt

    :params encoded_img: base64 encoded image

    :returns img: decoded numpy array
    """
    img_original = base64.b64decode(encoded_img)
    img_as_np = np.frombuffer(img_original, dtype=np.uint8)
    img = cv2.imdecode(img_as_np, cv2.IMREADH_UNCHANGED)

    return img

def process_stream(payload):
    global trip_wire_image
    global impeller_defect_image
    global impeller_explained_image
    stream_dict = json.loads(payload)
    stream_type = stream_dict['stream']
    if stream_type == INPUTFEED_NAME:
        trip_wire_image = decode(stream_dict['image'])
    elif stream_type == DEFECTFEED_NAME:
        impeller_defect_image = decode(stream_dict['image'])
        impeller_explained_image = decode(stream_dict['explainedimage'])

if __name__ == '__main__':
    init_model_explainer()
    client.loop_start()
    app.run(host='0.0.0.0')

