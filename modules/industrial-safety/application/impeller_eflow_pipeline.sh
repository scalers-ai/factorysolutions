#!/bin/bash

set -e

SCRIPTDIR="$(dirname "$(realpath "$0")")"

RTSPHOST=${1:-localhost}
RTSPPORT=${2:-8554}
MOSQUITTOSERVER=${3:-mosquittoserver}
IMPELLERVIDEOINPUT=${4}
INDUSTRIALSAFETYVIDEOINPUT=${5}
DEFECTDETECTION_FEED_NAME=${6}
INDUSTRIALSAFETY_FEED_NAME=${7}
INFLUX_ORG=${8}
INFLUX_TOKEN=${9}
INFLUX_BUCKET=${10}
INFLUX_HOST=${11}
INFLUX_PORT=${12}

# These are initialized from the eflow deployment manifest from the .env entries.
DEVICE=${DEFECT_TARGET_HARDWARE}
IOTHUB_DEVICE_ENDPOINT=${IOTHUB_DEVICE_DPS_ENDPOINT}
IOTHUB_DEVICE_SCOPE=${IOTHUB_DEVICE_DPS_ID_SCOPE}
IOTHUB_DEVICE_KEY=${IOTHUB_DEVICE_DPS_DEVICE_KEY}
IOTHUB_DEVICE_ID=${IOTHUB_DEVICE_DPS_DEVICE_ID}

IMPELLER_DEFECT_MODEL_PATH=/application/models/impeller-defect-custom/saved_model.xml
IMPELLER_DEFECT_MODEL_PROC_PATH=/application/models/impeller_model.json
DEFECT_DETECTION_SCRIPT_PATH=/application/postproc_callbacks/impeller_defects_post_process.py
INDUSTRIAL_SAFETY_MODEL_PATH=/application/models/person-detection/FP16/person-detection-retail-0013.xml
IMAGE_SERVER_SCRIPT=/application/imageserver/mjpg_server.py
INFERENCE_TIME_SCRIPT=/application/postproc_callbacks/inference_time.py
INDUSTRIAL_SAFETY_SCRIPT_PATH=/application/postproc_callbacks/industrial_safety.py
COORDINATES_FILE=/application/data/tripwire_coordinates.yml

# strt rtsp sim with the safety and defect feeds
tmux new -d ffmpeg -re -stream_loop -1 -i $IMPELLERVIDEOINPUT -c copy -f rtsp -rtsp_transport tcp rtsp://$RTSPHOST:$RTSPPORT/$DEFECTDETECTION_FEED_NAME

tmux new -d ffmpeg -re -stream_loop -1 -i $INDUSTRIALSAFETYVIDEOINPUT -c copy -f rtsp -rtsp_transport tcp rtsp://$RTSPHOST:$RTSPPORT/$INDUSTRIALSAFETY_FEED_NAME

# start the mjpg server script
tmux new -d python3 $IMAGE_SERVER_SCRIPT -m /application/models/impeller-defect-custom/hdf5/casting_product_detection.hdf5 -inflxh $INFLUX_HOST -inflxp $INFLUX_PORT -f $INDUSTRIALSAFETY_FEED_NAME -d $DEFECTDETECTION_FEED_NAME -mq $MOSQUITTOSERVER -o $INFLUX_ORG -t $INFLUX_TOKEN -b $INFLUX_BUCKET -cf $COORDINATES_FILE

#start the iotcentral device provisioning and telemetry script
tmux new -d python3 /application/iot_central/iot_central.py -m $MOSQUITTOSERVER -f $INDUSTRIALSAFETY_FEED_NAME -d $DEFECTDETECTION_FEED_NAME -dep $IOTHUB_DEVICE_ENDPOINT -dis $IOTHUB_DEVICE_SCOPE -dik $IOTHUB_DEVICE_KEY -did $IOTHUB_DEVICE_ID

sleep 10

echo Running impeller classification pipeline with the following parameters:

export GST_PLUGIN_PATH=${dl_streamer_lib_path}:/usr/lib/x86_64-linux-gnu/gstreamer-1.0:${GST_PLUGIN_PATH}

echo GST_PLUGIN_PATH=${GST_PLUGIN_PATH}

export GST_DEBUG=1

PIPELINE2="gst-launch-1.0 \
rtspsrc location=rtsp://$RTSPHOST:$RTSPPORT/$DEFECTDETECTION_FEED_NAME ! decodebin  ! videoconvert ! video/x-raw,format=BGRx ! \
gvapython module=$INFERENCE_TIME_SCRIPT class=InferenceTime ! \
gvaclassify model=$IMPELLER_DEFECT_MODEL_PATH model-proc=$IMPELLER_DEFECT_MODEL_PROC_PATH device=$DEVICE inference-region=full-frame ! \
gvapython module=$DEFECT_DETECTION_SCRIPT_PATH class=DefectDetection \
rtspsrc location=rtsp://$RTSPHOST:$RTSPPORT/$INDUSTRIALSAFETY_FEED_NAME ! decodebin  ! videoconvert ! video/x-raw,format=BGRx ! \
gvapython module=$INFERENCE_TIME_SCRIPT class=InferenceTime ! \
gvadetect model=$INDUSTRIAL_SAFETY_MODEL_PATH device=$DEVICE inference-interval=1 ! \
gvapython module=$INDUSTRIAL_SAFETY_SCRIPT_PATH class=TripWire ! \
gvametaconvert format=json add-tensor-data=true ! \
gvametapublish method=mqtt address=$MOSQUITTOSERVER:1883 topic=$INDUSTRIALSAFETY_FEED_NAME"

echo ${PIPELINE2}
tmux new -d ${PIPELINE2}

sleep infinity

