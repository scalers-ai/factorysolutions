import shap
import cv2
import matplotlib.pyplot as plt
import os
import numpy as np
from tensorflow.keras.models import Sequential, load_model
import argparse
from flask import Flask, render_template, Response
import logging as log
import glob
import io
import paho.mqtt.client as mqtt
import json
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WritePrecision
from datetime import datetime
import yaml
import time

ap = argparse.ArgumentParser()

ap.add_argument("-m", "--model", required=True,
                help="path to hdf5 model")
ap.add_argument("-inflxh", "--influxdbhost", required=True,
                help="InfluxDb host name")
ap.add_argument("-inflxp", "--influxdbport", required=True,
                help="InfluxDb port name")
ap.add_argument("-f", "--feedname", required=True,
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
INPUTFEED_NAME = args['feedname']
INFLUX_API_TOKEN=args['token']
INFLUX_ORG=args['organization']
MQTT_HOST = args['mqtthost']
HFD5_MODEL_PATH=args['model']
MQTT_CLIENT_NAME =   INPUTFEED_NAME + "-mqttclient2"
COORDINATES_FILE = args['tripwire_coordinates_file']

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

# load the yaml file for the coordinates.
def initialize_tripwire():
    global TRIPWIRE_COORDS
    with open(COORDINATES_FILE, "r") as data:
        # initialize trip wire polygon from yml file.
        TRIPWIRE_COORDS = yaml.safe_load(data)
        print("coordinates of trip wire are {}".format(TRIPWIRE_COORDS))

def on_disconnect(client, userdata,rc=0):
    log.debug("DisConnected result code "+str(rc))
    client.loop_stop()

def on_message(client, userdata, message):
    for id, tripwire in enumerate(TRIPWIRE_COORDS):
        check_occupancy(message.payload.decode("utf-8"), tripwire['coordinates'])
        log.debug("message topic=",message.topic)

def init_model_explainer():
    global explainer
    global model
    global client
    global db_client
    global write_api

    initialize_tripwire()
    # Init mqtt client
    client = mqtt.Client(MQTT_CLIENT_NAME) #create new instance
    client.connect(MQTT_HOST) #connect to broker
    log.debug("Subscribing to topic",INPUTFEED_NAME)
    client.subscribe(INPUTFEED_NAME)
    client.ondisconnect = on_disconnect
    client.on_message=on_message

    # Init influx client
    db_client = InfluxDBClient(url="http://{}:{}".format(IPADDRESS, INFLUXDBPORT), token=INFLUX_API_TOKEN, org=INFLUX_ORG)
    write_api = db_client.write_api(write_options=ASYNCHRONOUS)

    model = load_model(HFD5_MODEL_PATH)
    train_path = resources_path + 'train/'
    train_cases = ['ok_front/'+i for i in os.listdir(train_path + 'ok_front')]
    train_cases.extend(['def_front/'+i for i in os.listdir(train_path + 'def_front')])
    train_sample = [cv2.imread(train_path + i,
                    cv2.IMREAD_GRAYSCALE).reshape(1, *image_shape) / 255
                    for i in np.random.choice(train_cases, 3000, replace=False)]
    explainer = shap.DeepExplainer(model, train_sample[0])

def generate():
    captured_frames_list = glob.glob(resources_path + "impeller-classification*.jpg")
    while True:
        # Take only most recent file.
        time.sleep(0.01)
        if captured_frames_list:
            last_generated_frame = max(captured_frames_list, key=os.path.getctime)
            if last_generated_frame is not None:
                inferred_explained_frame = infer_explain_model(os.path.basename(last_generated_frame))
                yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + inferred_explained_frame.getvalue() + b'\r\n')
                inferred_explained_frame.close()
            else:
                empty_image = generate_empty_image()
                cv2.putText(img=empty_image, text='Empty Queue', org=(150, 250), fontFace=cv2.FONT_HERSHEY_TRIPLEX,
                            fontScale=3, color=(0, 255, 0),thickness=3)
                yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + empty_image.tobytes() + b'\r\n')

def generate_safety_feed():
    # Take only most recent file.
    captured_frames_list = glob.glob(resources_path + "industrial-safety*.jpg")
    while True:
        time.sleep(0.01)
        if captured_frames_list:
            last_generated_frame = max(captured_frames_list, key=os.path.getctime)
            if last_generated_frame is not None:
                img = cv2.imread(resources_path + os.path.basename(last_generated_frame))
                # render trip wire polygon
                for id, tripwire in enumerate(TRIPWIRE_COORDS):
                    pts = np.array(tripwire['coordinates'], np.int32)
                    # color to change based on whether there is a bounding box inside the polygon.
                    # red if tripwire tripped else green
                    if inside_tripwire:
                        color = (0, 0, 255)
                    else:
                        color = (0, 255, 0)
                    thickness = 2
                    image_with_tripwire = cv2.polylines(img, [pts],
                                          True, color, thickness)
                    encoded_image = cv2.imencode('.jpg', image_with_tripwire)
                    yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + encoded_image[1].tobytes() + b'\r\n')
            else:
                empty_image = generate_empty_image()
                cv2.putText(img=empty_image, text='No Data', org=(150, 250), fontFace=cv2.FONT_HERSHEY_TRIPLEX,
                            fontScale=3, color=(0, 255, 0),thickness=3)
                yield(b'--frame\r\n'b'Content-Type: image/jpeg\r\n\r\n' + empty_image.tobytes() + b'\r\n')

def generate_empty_image():
    return np.ones(shape=(300,300,1), dtype=np.int16)

def infer_explain_model(image_name):
    img = cv2.imread(resources_path + image_name, cv2.IMREAD_GRAYSCALE).reshape(1, *image_shape) / 255
    prediction = model.predict(img.reshape(1, *image_shape))
    if (prediction < 0.5):
        predicted_label = "Defective"
        prob = (1-prediction.sum()) * 100
    else:
        predicted_label = "OK"
        prob = prediction.sum() * 100

    shap_values = explainer.shap_values(img)
    shap.image_plot(shap_values, img, show=False)
    buf = io.BytesIO()

    # write accuracy and label
    defect_stats = Point("impeller_defect_stats") \
        .field("probability", prob) \
        .field("label", predicted_label) \
        .time(datetime.utcnow(), WritePrecision.NS)
    write_api.write(INFLUXBUCKET, INFLUX_ORG, defect_stats)

    plt.title('Impeller is {} \n Probability is {:.3f} %'.format(predicted_label, prob), weight='bold', size=12)
    plt.axis('off')
    buf.seek(0)
    plt.savefig(buf, format='png')
    plt.close()
    return buf

@app.route('/explainmodel')
def impeller_quality_video_feed():
    """
    Trigger the explainmodel() function on opening "0.0.0.0:5000/explainmodel" URL
    :return: image with explanation and inference details
    """
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/industrialsafety')
def safety_video_feed():
    """
    Trigger the safety_video_feed() function on opening "0.0.0.0:5000/explainmodel" URL
    :return: image with detections and tripwire overlays.
    """
    return Response(generate_safety_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

def check_occupancy(message_payload, tripwire_coords):
    global inside_tripwire
    detected_people_dict = json.loads(message_payload)

    for detected_people in detected_people_dict['objects']:
        detection = detected_people['detection']
        if detection['confidence'] > 0.85:
         x = detected_people['x']
         y = detected_people['y']
         w = detected_people['w']
         h = detected_people['h']
         person_id = detected_people['id']
         inside_tripwire = point_inside_polygon(x, y, w, h, tripwire_coords)
         safety_data = Point("industrial_safety_tripwire") \
             .tag("confidence", detection['confidence']) \
             .tag("person_id_tag", str(person_id)) \
             .field("status", inside_tripwire) \
             .field("person_id", person_id) \
             .time(datetime.utcnow(), WritePrecision.NS)
         write_api.write(INFLUXBUCKET, INFLUX_ORG, safety_data)
         #log to influx detections along with state whether tripped or not.


def point_inside_polygon(x, y, w, h, tripwire_coords, include_edges=True):
    p1x, p1y = tripwire_coords[0]
    p2x, p2y = tripwire_coords[1]
    p3x, p3y = tripwire_coords[2]
    p4x, p4y = tripwire_coords[3]
    inside = False
    centroid_x_of_detection = x + w/2
    centroid_y_of_detection = y + h/2
    log.debug("Centroid of detection : {},{} and minx {}, maxx {}, miny {}, maxy {}".format(centroid_x_of_detection,
            centroid_y_of_detection,
            min(p1x,p2x,p3x,p4x),
            max(p1x,p2x,p3x,p4x),
            min(p1y, p2y, p3y, p4y),
            max(p1y, p2y, p3y, p4y)))
    if centroid_x_of_detection >= min( p1x,p2x,p3x,p4x) and \
            centroid_x_of_detection <= max(p1x,p2x,p3x,p4x) and \
            centroid_y_of_detection >= min(p1y, p2y, p3y, p4y) and \
            centroid_y_of_detection <= max(p1y, p2y, p3y, p4y):
        log.debug("Trip wire is : {} and Detected Point is : {},{}".format(tripwire_coords, x, y))
        inside = True
    return inside

if __name__ == '__main__':
    init_model_explainer()
    client.loop_start()
    app.run(host='0.0.0.0')

