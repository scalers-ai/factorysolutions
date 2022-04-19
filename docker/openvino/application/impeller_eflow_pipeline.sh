#!/bin/bash

set -e

DEVICE=${1:-CPU}
RTSPHOST=${2:-localhost}
RTSPPORT=${3:-8554}
SCRIPTDIR="$(dirname "$(realpath "$0")")"
MOSQUITTOSERVER=${4:-mosquittoserver}
IMPELLERVIDEOINPUT=${5}
INDUSTRIALSAFETYVIDEOINPUT=${6}
DEFECTDETECTION_FEED_NAME=${7}
INDUSTRIALSAFETY_FEED_NAME=${8}
INFLUX_ORG=${9}
INFLUX_TOKEN=${10}
INFLUX_BUCKET=${11}
INFLUX_HOST=${12}
INFLUX_PORT=${13}

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
tmux new -d  python3 $IMAGE_SERVER_SCRIPT -m /application/models/impeller-defect-custom/hdf5/casting_product_detection.hdf5 -inflxh $INFLUX_HOST -inflxp $INFLUX_PORT -f $INDUSTRIALSAFETY_FEED_NAME -d $DEFECTDETECTION_FEED_NAME -mq $MOSQUITTOSERVER -o $INFLUX_ORG -t $INFLUX_TOKEN -b $INFLUX_BUCKET -cf $COORDINATES_FILE

sleep 10

echo Running impeller classification pipeline with the following parameters:

export GST_PLUGIN_PATH=${dl_streamer_lib_path}:/usr/lib/x86_64-linux-gnu/gstreamer-1.0:${GST_PLUGIN_PATH}

echo GST_PLUGIN_PATH=${GST_PLUGIN_PATH}

export GST_DEBUG=1

PIPELINE2="gst-launch-1.0 \
rtspsrc location=rtsp://$RTSPHOST:$RTSPPORT/$DEFECTDETECTION_FEED_NAME ! decodebin  ! videoconvert ! video/x-raw,format=BGRx ! \
gvaclassify model=$IMPELLER_DEFECT_MODEL_PATH model-proc=$IMPELLER_DEFECT_MODEL_PROC_PATH device=$DEVICE inference-region=full-frame ! \
gvapython module=$DEFECT_DETECTION_SCRIPT_PATH class=DefectDetection \
rtspsrc location=rtsp://$RTSPHOST:$RTSPPORT/$INDUSTRIALSAFETY_FEED_NAME ! decodebin  ! videoconvert ! video/x-raw,format=BGRx ! \
gvapython module=$INFERENCE_TIME_SCRIPT class=InferenceTime ! \
gvadetect model=$INDUSTRIAL_SAFETY_MODEL_PATH device=$DEVICE inference-interval=1 ! \
gvapython module=$INDUSTRIAL_SAFETY_SCRIPT_PATH class=TripWire ! \
gvametaconvert format=json add-tensor-data=true ! \
gvametapublish method=mqtt address=$MOSQUITTOSERVER:1883 topic=$INDUSTRIALSAFETY_FEED_NAME"

echo ${PIPELINE2}
nohup  ${PIPELINE2} &


sleep infinity

