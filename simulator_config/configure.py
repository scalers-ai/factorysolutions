"""
Copyright (C) 2021 scalers.ai
Automate Windows Simulator configurations

version: 1.0
"""
import configparser
import json
import os
import sys
import time
from argparse import ArgumentParser

import requests


def argparser() -> ArgumentParser:
    """
    Parse arguments from command line
    """
    parser = ArgumentParser()
    parser.add_argument("-ip", "--eflow_ip", required=True, type=str,
                        help="Enter the IP of the EFLOW VM")

    return parser


def generate_key(grafana_ip: str) -> str:
    """
    Generate API Key from Grafana

    :return api_key: Grafana API key
    """
    json_key = {
        "name": "apikey",
        "role": "Admin"
    }

    head = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    resp = requests.post(
        f'http://admin:admin@{grafana_ip}:3000/api/auth/keys',
        json=json_key, headers=head
    )

    if 200 != resp.status_code:
        print("API key with name apiKey already exists. Delete the key "
              " with name apiKey and try again.")
        exit(1)

    api_key = json.loads(json.dumps(resp.json()))['key']

    return api_key


def configure_grafana(eflow_ip: str, json_path: str, grafana_ip: str):
    # creat datasource
    datasource_paths = {
        os.path.join(json_path, 'influx_datasource.json'),
        os.path.join(json_path, 'testdata_datasource.json'),
    }
    for path in datasource_paths:
        with open(path, 'r') as source_file:
            datasource = json.load(source_file)
        head = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        if datasource["type"] != "testdata":
            datasource["url"] = datasource["url"].replace("<eflowIP>", eflow_ip)
        # datasource["url"] = f"http://{eflow_ip}:8086"
        resp= requests.post(
            f'http://admin:admin@{grafana_ip}:3000/api/datasources',
            json=datasource, headers=head
        )

        if 200 != resp.status_code:
            print("Unable to create the grafana datasource. Exiting")
            exit(1)

    print("Grafana datasource created.")

    time.sleep(10)
# create dashboards
    with open(os.path.join(json_path, 'defect_dashboard_windows.json'), 'r') as d_file:
        dashboard_data = d_file.read()
        dashboard_data = dashboard_data.replace("EFLOWIP", eflow_ip)
        dashboard = json.loads(dashboard_data)

    resp = requests.post(
        f'http://admin:admin@{grafana_ip}:3000/api/dashboards/db',
        json=dashboard, headers=head
    )

    if 200 != resp.status_code:
        print("Unable to create the grafana dashboard. Exiting")
        exit(1)
    
    with open(os.path.join(json_path, 'safety_dashboard_windows.json'), 'r') as d_file:

        dashboard_data = d_file.read()
        dashboard_data = dashboard_data.replace("EFLOWIP", eflow_ip)
        dashboard = json.loads(dashboard_data)

    resp = requests.post(
        f'http://admin:admin@{grafana_ip}:3000/api/dashboards/db',
        json=dashboard, headers=head
    )

    if 200 != resp.status_code:
        print("Unable to create the grafana dashboard. Exiting")
        exit(1)

    print("Grafana dashboards created.")


def update_telegraf(eflow_ip: str, config_path:str, api_key:str):
    """
    Update telegraf config

    :param eflow_ip: EFLOW VM IP
    :param config_path : Telegraf config file path
    :param api_key: Grafana API Key
    """
    telegraf_conf = os.path.join(config_path, 'telegraf.conf')
    with open(telegraf_conf, 'r') as conf_file:
        conf_data=conf_file.read()

    conf_data = conf_data.replace('<EFLOW_IP>', eflow_ip)
    updated_conf_data = conf_data.replace('<API_KEY>', api_key)

    # Write the file out again
    with open(telegraf_conf, 'w') as conf_file:
        conf_file.write(updated_conf_data)


def main():
    """Main method"""
    args = argparser().parse_args()
    eflow_ip = args.eflow_ip

    grafana_ip = "127.0.0.1"
    json_path = ".\\"

    # generate grafana api key
    api_key = generate_key(grafana_ip)

    # configure dashboard and datasource in grafana
    configure_grafana(eflow_ip, json_path, grafana_ip)

    # configure telegraf config file
    config_path = "C:\Program Files\InfluxData\\telegraf"
    update_telegraf(eflow_ip, config_path, api_key)


if __name__ == "__main__":
    main()
