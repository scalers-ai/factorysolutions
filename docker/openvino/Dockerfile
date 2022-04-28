FROM openvino/ubuntu20_data_dev

USER root

RUN apt-get update && apt-get install -y git  clinfo wget gnupg gpg-agent software-properties-common nfs-common tmux vim

WORKDIR /root/neo

RUN wget https://github.com/intel/compute-runtime/releases/download/22.10.22597/intel-gmmlib_22.0.2_amd64.deb && wget https://github.com/intel/intel-graphics-compiler/releases/download/igc-1.0.10409/intel-igc-core_1.0.10409_amd64.deb && wget https://github.com/intel/intel-graphics-compiler/releases/download/igc-1.0.10409/intel-igc-opencl_1.0.10409_amd64.deb && wget https://github.com/intel/compute-runtime/releases/download/22.10.22597/intel-opencl-icd_22.10.22597_amd64.deb && wget https://github.com/intel/compute-runtime/releases/download/22.10.22597/intel-level-zero-gpu_1.3.22597_amd64.deb

RUN dpkg -i /root/neo/*.deb

ADD application /application
WORKDIR /application

RUN chmod u+x /application/impeller_eflow_pipeline.sh

RUN chmod u+x /opt/intel/openvino/install_dependencies/install_openvino_dependencies.sh

RUN apt -y install sudo wget nano ffmpeg zip unzip

RUN python3 -m pip install flask influxdb-client paho-mqtt opencv-python shap opcua gdown azure-iot-device==2.9.0 tf-explain

WORKDIR /application/resources

RUN gdown https://drive.google.com/uc?id=19DMtkOqP99eNVO5SEqhIDrxTMp6tGpWT -O train.zip

RUN unzip -o train.zip

RUN rm -rf train.zip

EXPOSE 5000

CMD ["bash", "-c", "source /opt/intel/openvino/bin/setupvars.sh && cd /application && ./impeller_eflow_pipeline.sh CPU simplertspserver 8554 mosquittoserver /application/sample_videos/impeller.mp4 /application/sample_videos/people-detection.mp4 defectdetection industrialsafety acmeindustries defect_tracking Industrial_Detection_Safety influxdb 8086 global.azure-devices-provisioning.net 0ne005AC2F0 P8St3G12DUhrT9L71feMwPDFvWK0yXwBurCXFdHWK70= r5ltef9mn9"]
