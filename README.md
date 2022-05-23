# Industrial Safety and Impeller Defect Detection Setup Guide

# Prerequisites
1. An development edge machine with Ubuntu/WSL2.
2. A deployment machine with
    * Windows 10/11 (Pro, Enterprise, IoT Enterprise). Build greater than or equal to 19044.
    * Minimum of Intel® Core™ i7 processor (with Intel ® Virtualization Technology and iGPU) with 6th Gen or greater.
3. Azure Account with active suscription. Follow [this documentation](https://azure.microsoft.com/en-us/free/
) for know more about Creating Azure Account.

# View the video tutorials here
[Youtube Tutorials](https://www.youtube.com/channel/UCAtxB_-2wHiJrfW4d7cd3Pw/featured)

# Setup
## Setting up Development machine

> Note: Follow [this](https://docs.microsoft.com/en-us/windows/wsl/install) document for setting up Windows Subsystem For Linux (WSL2) on your Windows machine.

Complete the following steps to setup the deployment machine.
1. [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
    > Note: Add the non-root user to the docker group by following [Manage Docker as a non-root user](https://docs.docker.com/engine/install/linux-postinstall/#manage-docker-as-a-non-root-user).
2. [Install Visual Studio Code](https://code.visualstudio.com/download)
3. Install [Azure IoT Tools Extension](https://marketplace.visualstudio.com/items?itemName=vsciot-vscode.azure-iot-tools) for visual studio code.

## Setting up Cloud Resources
1. Create [Azure Resource Group](https://docs.microsoft.com/en-us/azure/azure-resource-manager/management/manage-resource-groups-portal#create-resource-groups)
2. Create [Azure IoT Hub](https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-create-through-portal#create-an-iot-hub)
<a id="iotedge"> </a>

3. Create Azure IoT Edge Device using [Register your device](https://docs.microsoft.com/en-us/azure/iot-edge/how-to-provision-single-device-linux-symmetric?view=iotedge-2020-11&tabs=azure-portal#register-your-device) section.

<a id="container-registry"> </a>

4. Create [Azure Container Registry](https://docs.microsoft.com/en-us/azure/azure-video-analyzer/video-analyzer-docs/edge/get-started-detect-motion-emit-events-portal#create-a-container-registry). 

    * **Note**: Get `CONTAINER_REGISTRY_USERNAME` and `CONTAINER_REGISTRY_PASSWORD` from the container registry created on step [Create Azure Container Registry](#container-registry).
    
        * Navigate to **Settings > Access Keys** and enable Admin User.
        * use the **Registry name** and **password** to update the file.

5. Setting up Azure IoT Central
    1. Create [Azure IoT Central Application](https://docs.microsoft.com/en-us/azure/iot-central/core/quick-deploy-iot-central#create-an-application).

    <a id="central_device"> </a>

    2. Create [Azure IoT Central Device](https://docs.microsoft.com/en-us/azure/iot-central/core/quick-deploy-iot-central#register-a-device) for the Azure IoT Central application  created on the previous step.

        * **Note**: Click on the **Connect** option on the created to get `IOTHUB_DEVICE_DPS_ID_SCOPE` (ID Scope), `IOTHUB_DEVICE_DPS_DEVICE_ID` (Device ID) and `IOTHUB_DEVICE_DPS_DEVICE_KEY` (Primary Key) values.

    3. Create a **Device Template** by following the below steps
        
        * Open **Device Template** on the IoT Central application created.        
        * Click on **New** and select **IoT Device** as type to select a custom device template.
        * Provide a name for the template (eg. smart port) and click on **Review** and then on **Create**.
        * Once created, open the **Device template** (smart port) and click on **Import a Model**.
        * Select the file *iot_central/app.json* as the model file.
        * Click on **Publish** to publish the template.

## Setting up Deployment Machine

1. Setting up the EFLOW on your Windows deployment machine follow [EFLOW-GPU](./eflow_gpu_setup.md) documentation.

<br>

# Deploying the Solution
> Note: This step assumes that you have successfully completed installing EFLOW on your deployment Windows machine.

> These steps needs to be done from your development machine **not** deployment machine. 
## Connect Visual Studio Code to the IoT Hub
1. Follow [Obtain your IoT Hub connection string](https://docs.microsoft.com/en-us/azure/azure-video-analyzer/video-analyzer-docs/edge/get-started-detect-motion-emit-events-portal#obtain-your-iot-hub-connection-string) to copy your IoT Hub connection string.
2. Open the **Explorer** tab by naviagting to **View > Explorer** on the Visual Studio Code
2.  Open **Azure IOT HUB** from the lower-left corner of your visual studio code on **Explore Tab**.
3.  Click on the **More Action** to set the IoT Hub Connection string and paste the Primary Connection String copied on step 1 on the pop up input box shown and press **Enter** key.
4. After successfull setup, **Azure IOT HUB** from the lower-left corner of your visual studio code will list the IoT Edge Devices under your Azure IoT Hub.

## Building and Pushing Docker images

1. Open the cloned repo in the Visual Studio Code using **File > Open Folder**
2. Expand the **FACTORYSOLUTIONS** folder.
3. Update the **.env** file with the following details

    | Variable | Description | Default |
    | --- | --- | --- |
    | `CONTAINER_REGISTRY_USERNAME` | Azure Container Registry Username. Refer step [Create Azure Container Registry](#container-registry) |  |
    | `CONTAINER_REGISTRY_PASSWORD` |  Azure Continer Registry Password. Refer step [Create Azure Container Registry](#container-registry) |  |
    | `DEFECT_TARGET_HARDWARE` | The Model Target Hardware. Avilable options: CPU/GPU | `CPU` |
    | `IOTHUB_DEVICE_DPS_ENDPOINT` | Azure IoT Device Provision Service endpoint | `global.azure-devices-provisioning.net` |
    | `IOTHUB_DEVICE_DPS_ID_SCOPE` | IoT Central Device ID Scope. Refer [Creating Azure IoT Central Device](#central_device)| | 
    | `IOTHUB_DEVICE_DPS_DEVICE_ID` | IoT Central Device ID. Refer [Creating Azure IoT Central Device](#central_device) | |
    | `IOTHUB_DEVICE_DPS_DEVICE_KEY` | IoT Central Device Key.Refer [Creating Azure IoT Central Device](#central_device) | |

4. Building and pushing the solutions
    
    * For **CPU**, right click on the `deployment.template.json` and then select **Build and Push IoT Edge Solution**.
    * For **GPU**, right click on the `deployment.template.gpu.json` and then select **Build and Push IoT Edge Solution**.
    
    The above step generates the deployment manifest file namely `deployment.amd64.json` or `deployment.gpu.amd64.json` 
    based on whether CPU or GPU template was chosen above in the **config** folder.

## Deploying the Solution 
Continue to deploy the solution to your deployment machine once all the module are build and pushed.

1. Right click on the `config/deployment.amd64.json` (or `config/deployment.amd64.gpu.json` if you want to run on the GPU) file 
and select **Generate Deployment for Single Device**.
2. Select the IoT Edge Device ID from the pop box that appears.
3. An OUTPUT window will pop up confirming that the deployment has succeeded.

## Verify the deployment

The deployment can be verified in multiple ways, here we will be verifying the deployment directly on deployment Windows machine.

1. Open a **Power Shell** on your deployment machine.
2. Run the following command to ssh to the EFLOW virtual machine from your windows machine.

    ```sh
    Connect-EflowVM
    ```
2. Run the following command to list all the deployed modules

    ```sh
    sudo iotedge list
    ```
3. Wait until the following modules appear on the list with status as running
    * edgeAgent
    * edgeHub
    * telegraf
    * grafana
    * mosquittoserver
    * rtspserver
    * opcua
    * influxdb
    * industrial-safety

    Run the command on step 2 to recheck the module status.

The same can be viewed from
* Visual Studio Code - Azure IOT HUB panel
* Azure IoT Hub portal
* Windows Admin Center dashboard
