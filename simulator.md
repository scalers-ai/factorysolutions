# Setting up Simulator on Windows


1. Setup Grafana on Windows
    1. To install grafana on the Windows machine follow [this documentation](https://grafana.com/grafana/download/8.3.2?edition=oss&platform=windows) to download windows installer file and run it to install the application.

        > Note: Install Grafana version 8.3.2 with OSS Edition.

    2. Open a **Command Prompt** as **Administrator**.
    
    3. Run the below command to setup the Grafana configurations.

        ```sh
        cd <path to repo>\simulator_configs

        setup_grafana.bat
        ```


2. Setting up Telegraf on Windows

    1. Open a **Command Prompt** as an **Administrator**.

    2. To install and setup Telegraf on windows, run the `simulator_configs/setup_telegraf.bat` file

        ```sh
        cd <path to repo>\simulator_configs
        
        setup_telegraf.bat
        ```

    3. Run the command the below command to get the EFLOW VM IP on a power shell
    
        ```sh
        Get-eflowVmAddr
        ```

    4. Run the configuration script with the EFLOW IP from the previous step

        ```sh
        cd <path to repo>\simulator_configs

        python3 configure.py -ip <EFLOW IP>
        ```


    3. Run the below command to setup the Telegraf configuration file and create Grafana UI dashboards

       ```sh
        cd "C:\Program Files\InfluxData\telegraf\"

        telegraf.exe --service install --config "C:\Program Files\InfluxData\telegraf\telegraf.conf"

        telegraf.exe --service start
        ```

# Visualize UI Windows

* Open the URL [localhost:3000](http://localhost:5000) on your Windows Deployment machine to open the Grafana dashboard.

* Open the dashboard **Defect Detection - Windows** from the dashboard list to see Impeller Defect Detection view.

* Open the dashboard **Safety Dashboard - Windows** from the dashboard list to view the Tripwire Safety Dashboard view.

