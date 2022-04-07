#!/bin/bash

set -e

DEVICE=${1:-CPU}

RTSPHOST=${2:-localhost}

RTSPPORT=${3:-8554}

SCRIPTDIR="$(dirname "$(realpath "$0")")"

MOSQUITTOSERVER=${4:-mosquittoserver}

IMPELLERVIDEOINPUT=${5}

IMPELLER_DEFECT_MODEL_PATH=/application/models/impeller-defect-custom/saved_model.xml
IMPELLER_DEFECT_MODEL_PROC_PATH=/application/models/impeller_model.json
PYTHON_SCRIPT=/application/postproc_callbacks/impeller_defects_post_process.py

INDUSTRIAL_SAFETY_MODEL_PATH=/application/models/person-detection/FP16/person-detection-retail-0013.xml
INDUSTRIALSAFETYVIDEOINPUT=/application/sample_videos/people-detection.mp4

# strt rtsp
tmux new -d ffmpeg -re -stream_loop -1 -i $IMPELLERVIDEOINPUT -c copy -f rtsp -rtsp_transport tcp rtsp://$RTSPHOST:$RTSPPORT/defectdetection

tmux new -d ffmpeg -re -stream_loop -1 -i $INDUSTRIALSAFETYVIDEOINPUT -c copy -f rtsp -rtsp_transport tcp rtsp://$RTSPHOST:$RTSPPORT/industrialsafety

echo Running impeller defect detection with the following parameters:

export GST_PLUGIN_PATH=${dl_streamer_lib_path}:/usr/lib/x86_64-linux-gnu/gstreamer-1.0:${GST_PLUGIN_PATH}

echo GST_PLUGIN_PATH=${GST_PLUGIN_PATH}

export GST_DEBUG=1

sleep 5

# start the mqtt listener

MQTTLISTENTER_ANALYTICS_SCRIPT=/application/mqttlisteners/impeller_classification_event_listener.py

tmux new -d python3 $MQTTLISTENTER_ANALYTICS_SCRIPT -inflxh influxdb -inflxp 8086 -f defectdetection -m $MOSQUITTOSERVER

echo Running impeller classification pipeline with the following parameters:

PIPELINE2="gst-launch-1.0 \
urisourcebin uri=rtsp://$RTSPHOST:$RTSPPORT/defectdetection ! queue ! decodebin  ! videoconvert ! \
gvaclassify model=$IMPELLER_DEFECT_MODEL_PATH model-proc=$IMPELLER_DEFECT_MODEL_PROC_PATH device=$DEVICE inference-interval=5 inference-region=full-frame ! \
gvapython module=$PYTHON_SCRIPT ! \
gvametaconvert format=json json-indent=4 ! \
gvametapublish method=mqtt address=$MOSQUITTOSERVER:1883 topic=defectdetection ! queue ! \
gvawatermark ! x264enc ! rtspclientsink location=rtsp://$RTSPHOST:$RTSPPORT/defectdetection.inference protocols=udp sync=false"

echo ${PIPELINE2}
nohup ${PIPELINE2} &

echo Running industrial safety pipeline with the following parameters:

export GST_PLUGIN_PATH=${dl_streamer_lib_path}:/usr/lib/x86_64-linux-gnu/gstreamer-1.0:${GST_PLUGIN_PATH}

echo GST_PLUGIN_PATH=${GST_PLUGIN_PATH}


PIPELINE1="gst-launch-1.0 \
urisourcebin uri=rtsp://$RTSPHOST:$RTSPPORT/industrialsafety ! queue ! decodebin  ! videoconvert ! \
gvadetect model=$INDUSTRIAL_SAFETY_MODEL_PATH device=$DEVICE inference-interval=4 ! queue ! \
gvawatermark ! gvatrack tracking-type=short-term ! queue ! \
gvametaconvert format=json json-indent=4 ! \
gvametapublish method=mqtt address=$MOSQUITTOSERVER:1883 topic=industrialsafety ! queue ! \
gvawatermark ! x264enc ! rtspclientsink location=rtsp://$RTSPHOST:$RTSPPORT/industrialsafety.inference protocols=udp sync=false"

echo ${PIPELINE1}
nohup ${PIPELINE1} &

sleep infinity
