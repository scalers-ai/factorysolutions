#!/usr/bin/env python3

import paho.mqtt.client as mqtt
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WritePrecision
import json
import argparse
from datetime import datetime
import logging

ap = argparse.ArgumentParser()

ap.add_argument("-inflxh", "--influxdbhost", required=True,
                help="InfluxDb host name")
ap.add_argument("-inflxp", "--influxdbport", required=True,
                help="InfluxDb port name")
ap.add_argument("-f", "--feedname", required=True,
                help="The actual name of the feed")
ap.add_argument("-m", "--mqtthost", required=True,
                help="The mqtt host name")
ap.add_argument("-o", "--organization", required=True,
                help="The org. against which influx data is logged")
ap.add_argument("-t", "--token", required=True,
                help="The influx token to read/ write data")
ap.add_argument("-b", "--bucket", required=True,
                help="The influx bucket to read/ write data")

args = vars(ap.parse_args())

# connect to influx and create a client
IPADDRESS = args['influxdbhost']
INFLUXDBPORT = args['influxdbport']
INFLUXBUCKET = args['bucket']
INPUTFEED_NAME = args['feedname']
MQTT_HOST = args['mqtthost']
IMPELLER_INDEX = 0
INFLUX_API_TOKEN=args['token']
INFLUX_ORG=args['organization']

MQTT_CLIENT_NAME = INPUTFEED_NAME + "-mqttclient1"

proxy = {"http": "http://{}:{}".format(IPADDRESS, INFLUXDBPORT)}
db_client = InfluxDBClient(url="http://{}:{}".format(IPADDRESS, INFLUXDBPORT), token=INFLUX_API_TOKEN, org=INFLUX_ORG)
write_api = db_client.write_api(write_options=ASYNCHRONOUS)

broker_address=MQTT_HOST
client = mqtt.Client(MQTT_CLIENT_NAME) #create new instance
client.connect(broker_address) #connect to broker
print("Subscribing to topic",INPUTFEED_NAME)
client.subscribe(INPUTFEED_NAME)

def on_disconnect(client, userdata,rc=0):
    logging.debug("DisConnected result code "+str(rc))
    client.loop_stop()

client.ondisconnect = on_disconnect

def on_message(client, userdata, message):
    global IMPELLER_INDEX
    logging.debug("message received " ,str(message.payload.decode("utf-8")))
    detected_vehicles_dict = json.loads(str(message.payload.decode("utf-8")))
    for i in detected_vehicles_dict['objects']:
        detected_impeller_dict = i['detection']
        confidence = detected_impeller_dict['confidence']
        label = detected_impeller_dict['label']
        impeller_status = 1
        if label == 'Defective':
            impeller_status = 0
        data = Point("impeller_defects") \
            .tag("confidence", str(confidence)) \
            .tag("label", str(label)) \
            .field("status", impeller_status) \
            .field("impeller_id", IMPELLER_INDEX) \
            .time(datetime.utcnow(), WritePrecision.NS)
        IMPELLER_INDEX = IMPELLER_INDEX + 1
        write_api.write(INFLUXBUCKET, INFLUX_ORG, data)
client.on_message=on_message
client.loop_forever()

