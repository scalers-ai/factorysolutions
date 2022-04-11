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
PYTHON_SCRIPT=/application/postproc_callbacks/impeller_defects_post_process.py
INDUSTRIAL_SAFETY_MODEL_PATH=/application/models/person-detection/FP16/person-detection-retail-0013.xml

# strt rtsp
tmux new -d ffmpeg -re -stream_loop -1 -i $IMPELLERVIDEOINPUT -c copy -f rtsp -rtsp_transport tcp rtsp://$RTSPHOST:$RTSPPORT/$DEFECTDETECTION_FEED_NAME

tmux new -d ffmpeg -re -stream_loop -1 -i $INDUSTRIALSAFETYVIDEOINPUT -c copy -f rtsp -rtsp_transport tcp rtsp://$RTSPHOST:$RTSPPORT/$INDUSTRIALSAFETY_FEED_NAME

echo Running impeller defect detection with the following parameters:

export GST_PLUGIN_PATH=${dl_streamer_lib_path}:/usr/lib/x86_64-linux-gnu/gstreamer-1.0:${GST_PLUGIN_PATH}

echo GST_PLUGIN_PATH=${GST_PLUGIN_PATH}

export GST_DEBUG=1

sleep 5

# start the mqtt listener

MQTTLISTENTER_ANALYTICS_SCRIPT=/application/mqttlisteners/impeller_classification_event_listener.py
MODEL_EXPLAINER_SCRIPT=/application/modelexplainability/explain_model.py
COORDINATES_FILE=/application/data/tripwire_coordinates.yml

# start the ai explainability script

nohup python3 $MODEL_EXPLAINER_SCRIPT -m /application/models/impeller-defect-custom/hdf5/casting_product_detection.hdf5 -inflxh $INFLUX_HOST -inflxp $INFLUX_PORT -f $INDUSTRIALSAFETY_FEED_NAME -mq $MOSQUITTOSERVER -o $INFLUX_ORG -t $INFLUX_TOKEN -b $INFLUX_BUCKET -cf $COORDINATES_FILE &

sleep 10

tmux new -d python3 $MQTTLISTENTER_ANALYTICS_SCRIPT -inflxh $INFLUX_HOST -inflxp $INFLUX_PORT -f $DEFECTDETECTION_FEED_NAME -m $MOSQUITTOSERVER -o $INFLUX_ORG -t $INFLUX_TOKEN -b $INFLUX_BUCKET

echo Running impeller classification pipeline with the following parameters:

PIPELINE2="gst-launch-1.0 \
urisourcebin uri=rtsp://$RTSPHOST:$RTSPPORT/$DEFECTDETECTION_FEED_NAME ! \
queue ! decodebin  ! videoconvert ! \
gvaclassify model=$IMPELLER_DEFECT_MODEL_PATH model-proc=$IMPELLER_DEFECT_MODEL_PROC_PATH device=$DEVICE inference-region=full-frame ! \
gvapython module=$PYTHON_SCRIPT ! \
gvametaconvert format=json json-indent=4 ! \
gvametapublish method=mqtt address=$MOSQUITTOSERVER:1883 topic=$DEFECTDETECTION_FEED_NAME ! tee name=t \
t. ! queue ! videorate ! video/x-raw,framerate=1/8 ! jpegenc ! multifilesink location=/application/resources/impeller-classification.jpg \
t. ! queue ! gvawatermark ! x264enc ! rtspclientsink location=rtsp://$RTSPHOST:$RTSPPORT/$DEFECTDETECTION_FEED_NAME.inference protocols=udp sync=false"

echo ${PIPELINE2}
nohup ${PIPELINE2} &


echo Running industrial safety pipeline with the following parameters:

export GST_PLUGIN_PATH=${dl_streamer_lib_path}:/usr/lib/x86_64-linux-gnu/gstreamer-1.0:${GST_PLUGIN_PATH}

echo GST_PLUGIN_PATH=${GST_PLUGIN_PATH}

PIPELINE1="gst-launch-1.0 \
urisourcebin uri=rtsp://$RTSPHOST:$RTSPPORT/$INDUSTRIALSAFETY_FEED_NAME ! queue ! decodebin  ! videoconvert ! \
gvadetect model=$INDUSTRIAL_SAFETY_MODEL_PATH device=$DEVICE ! \
gvawatermark ! gvatrack tracking-type=short-term ! queue ! \
gvametaconvert format=json json-indent=4 ! \
gvametapublish method=mqtt address=$MOSQUITTOSERVER:1883 topic=$INDUSTRIALSAFETY_FEED_NAME ! \
gvawatermark ! videorate ! video/x-raw,framerate=1/1 ! jpegenc ! multifilesink location=/application/resources/industrial-safety.jpg"

echo ${PIPELINE1}
nohup ${PIPELINE1} &

sleep infinity

