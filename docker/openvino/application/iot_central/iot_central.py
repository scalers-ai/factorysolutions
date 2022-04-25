import os
import asyncio
import json
import time
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from os import devnull
from webbrowser import get

from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device.aio import ProvisioningDeviceClient
from azure.iot.device import constant, Message, MethodResponse
from datetime import date, timedelta, datetime
import argparse

#from mqtt_sub import MQTTSub
import paho.mqtt.client as mqtt

safety_data = None
defect_data = None

ap = argparse.ArgumentParser()

ap.add_argument("-m", "--mqtthost", required=True,
                help="The mqtt host name")
ap.add_argument("-f", "--safetyfeedname", required=True,
                help="The mqtt topic to listen to")
ap.add_argument("-d", "--defectfeedname", required=True,
                help="The mqtt topic to listen to")
ap.add_argument("-dep", "--iothub_device_endpoint", required=True,
                help="The iot hub device endpoint")
ap.add_argument("-dis", "--iothub_device_id_scope", required=True,
                help="The iot hub device id scope")
ap.add_argument("-dik", "--iothub_device_id_key", required=True,
                help="The iot hub device id key")
ap.add_argument("-did", "--iothub_device_id", required=True,
                help="The iot hub device id")

args = vars(ap.parse_args())

MQTT_HOST = args['mqtthost']
SAFETYFEED_NAME = args['safetyfeedname']
DEFECTFEED_NAME = args['defectfeedname']
IOTHUB_DEVICE_ENDPOINT = args['iothub_device_endpoint']
IOTHUB_DEVICE_ID_SCOPE = args['iothub_device_id_scope']
IOTHUB_DEVICE_ID_KEY = args['iothub_device_id_key']
IOTHUB_DEVICE_ID = args['iothub_device_id']

async def provision_device(provisioning_host, id_scope, registration_id, symmetric_key, model_id):
    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
        provisioning_host=provisioning_host,
        registration_id=registration_id,
        id_scope=id_scope,
        symmetric_key=symmetric_key,
    )
    provisioning_device_client.provisioning_payload = {"modelId": model_id}
    return await provisioning_device_client.register()

def on_message(client, userdata, message):
    global safety_data
    global defect_data
    payload = message.payload.decode("utf-8")
    stream_dict = json.loads(payload)
    stream_type = stream_dict['stream']
    if stream_type == SAFETYFEED_NAME:
        safety_data = stream_dict
    elif stream_type == DEFECTFEED_NAME:
        defect_data = stream_dict    


def get_details(mqtt_client, msg_type):
    if msg_type == SAFETYFEED_NAME:
        if safety_data != None:
            safety_data['image'] = ''
            return safety_data
    elif msg_type == DEFECTFEED_NAME:
        if defect_data != None:
            defect_data['image'] = ''
            return defect_data   
        

async def main():
    model_id = "industrialSafetyAndDefectDetectionApp:1"
    encoding = "utf-8"
    content_type = "application/json"
    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_HOST, 1883, 60)
    mqtt_client.subscribe(SAFETYFEED_NAME)
    mqtt_client.subscribe(DEFECTFEED_NAME)
    mqtt_client.on_message = on_message
    mqtt_client.loop_start()

    provisioning_host = IOTHUB_DEVICE_ENDPOINT
    id_scope = IOTHUB_DEVICE_ID_SCOPE
    registration_id =  IOTHUB_DEVICE_ID
    symmetric_key = IOTHUB_DEVICE_ID_KEY

    registration_result = await provision_device(
        provisioning_host, id_scope, registration_id, symmetric_key, model_id
    )
    #print("Registration result is {}".format(registration_result.status))
    if registration_result.status == "assigned":
        device_client = IoTHubDeviceClient.create_from_symmetric_key(
            symmetric_key=symmetric_key,
            hostname=registration_result.registration_state.assigned_hub,
            device_id=registration_result.registration_state.device_id,
            product_info=model_id,
        )

    # Connect the client.
    await device_client.connect()

    while True:

        # send safety details
        safety_data = get_details(mqtt_client, SAFETYFEED_NAME)
        safety_msg = Message(json.dumps(safety_data))
        safety_msg.content_encoding = encoding
        safety_msg.content_type = content_type

        print("Sending message to IOT CENTRAL {}".format(safety_msg))
        await device_client.send_message(safety_msg)

        defect_data = get_details(mqtt_client, DEFECTFEED_NAME)
        defect_msg = Message(json.dumps(defect_data))
        defect_msg.content_encoding = encoding
        defect_msg.content_type = content_type

        print("Sending message to IOT CENTRAL {}".format(defect_msg))
        await device_client.send_message(defect_msg)
        time.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())