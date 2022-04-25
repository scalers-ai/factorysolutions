#!/usr/bin python3
# Copyright (C) 2021 scalers.ai
# Version: 1.0

import time
import paho.mqtt.client as mqtt
import json


SAFETYFEED_NAME="industrialsafety"
DEFECTFEED_NAME="defectdetection"
MQTT_HOST="mosquittoserver"
safety_data = None
defect_data = None

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
        if safety_data is not None:
            safety_data['image'] = ''
            return safety_data
    elif msg_type == DEFECTFEED_NAME:
        if defect_data is not None:
            defect_data['image'] = ''
            return defect_data


def stream_data() -> None:
    """Stream inference results by reading data from industrialsafety and defectdetectiontopics"""
    mqtt_client = mqtt.Client()
    mqtt_client.connect(MQTT_HOST, 1883, 60)
    mqtt_client.subscribe(SAFETYFEED_NAME)
    mqtt_client.subscribe(DEFECTFEED_NAME)
    mqtt_client.on_message = on_message
    mqtt_client.loop_start()

    while True:
        current_time = int(time.time() * 1000000000)
        defect_data = get_details(mqtt_client, DEFECTFEED_NAME)
        safety_data = get_details(mqtt_client, SAFETYFEED_NAME)

        if safety_data is not None:
            # print safety data
            safety = ("industrial-safety-stream,stream={} person_count={},violations={},fps={},target=\"{}\""
                    " {} \n").format(
                "industrialsafety", safety_data['person_count'],
                safety_data['violations'],
                safety_data['fps'],
                safety_data['target'],
                current_time
            )
            print(safety)

        if defect_data is not None:
            # print defect data
            defects = ("defect-detection-stream,stream={} impeller_status_n={},accuracy={},fps={},target=\"{}\""
                    " {} \n").format(
                "defectdetection", defect_data['defects'],
                defect_data['accuracy'],
                defect_data['fps'],
                defect_data['target'],
                current_time
            )
            print(defects)
        time.sleep(0.01)


if __name__ == "__main__":
    stream_data()
