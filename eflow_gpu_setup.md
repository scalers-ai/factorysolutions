# Enable GPU-PV on Azure EFLOW

Follow the below steps to enable **Intel iGPU** para virtualization on Azure Eflow.

## 1. Enable Hyper-V

Follow instructions below to enable the Hyper-V feature using PowerShell.
1. Open an elevated PowerShell console and run the following command:

    ```powershell
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
    ```

2. Reboot machine when prompted.

## 2. Install Intel® Graphics Driver (with WSL GPU support)
Follow the instructions below to update the graphics driver.
1. Download and install Intel® Graphics driver (version 30.0.100.9955) from [Intel® Graphics – Windows* DCH Drivers](https://www.intel.com/content/www/us/en/download/19344/intel-graphics-windows-dch-drivers.html)


##  3. WSL Installation
Follow the instructions below to install WSL.

1. Open an elevated PowerShell console and run the following command:

    ```powershell
    wsl --install
    ```
2. Reboot machine when prompted.

## 4. EFLOW Installation
Follow the instructions below to download and install EFLOW on your Windows* system.
    
1. In the PowerShell console, run the following commands to download EFLOW.

    ```powershell
    $msiPath = $([io.Path]::Combine($env:TEMP, 'AzureIoTEdge.msi'))

    $ProgressPreference = 'SilentlyContinue'

    Invoke-WebRequest "https://aka.ms/AzEflowMSI" -OutFile $msiPath
    ```

2. Install EFLOW

    ```powershell
    Start-Process -Wait msiexec -ArgumentList "/i","$([io.Path]::Combine($env:TEMP, 'AzureIoTEdge.msi'))","/qn"
    ```

## 5. EFLOW Deployment

1. In an elevated PowerShell console, run the following command to deploy EFLOW:

    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force
    Import-Module AzureEFLOW
    $cpu_count = 4
    $memory = 4096
    $hard_disk = 30
    $gpu_name = (Get-WmiObject win32_VideoController | where{$_.name -like "Intel(R)*"}).caption
    ```

    ```powershell
    Deploy-Eflow -acceptEula yes -acceptOptionalTelemetry no -headless -cpuCount $cpu_count -memoryInMB $memory -vmDiskSize $hard_disk -gpuName $gpu_name -gpuPassthroughType ParaVirtualization -gpuCount 1
    ```

## 6. Verify the Setup
1. Run the below commands to connect to EFLOW
    ```powershell
    Connect-EflowVM
    ```
2. Run the below command inside the EFLOW VM to verify that the `/dev/dxg` node is exposed.
    ```sh
    ls -la /dev/dxg
    ```

    The command should result in the follow ouput.
    ```sh
    crw-rw-rw- 1 root root 10, 60 Jan  7 06:26 /dev/dxg
    ```

## 7. Provision the device with its cloud identity

1. Run the below command on a **PowerShell** as *Administrator*.

    ```powershell
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force
    Import-Module AzureEFLOW
    ```

2. Obtain the *Primary Connection String* of the Azure IoT Edge Device using [Obtain your IoT Hub connection string](https://docs.microsoft.com/en-us/azure/azure-video-analyzer/video-analyzer-docs/edge/get-started-detect-motion-emit-events-portal#obtain-your-iot-hub-connection-string).

    ```powershell
    Provision-EflowVm -provisioningType ManualConnectionString -devConnString "<Primary Connection String>" -headless
    ```


