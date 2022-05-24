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
        "name": "apikey4",
        "role": "Admin"
    }

    head = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    resp = requests.post(
        f'http://admin:admin@{grafana_ip}:3001/api/auth/keys',
        json=json_key, headers=head
    )

    if 200 != resp.status_code:
        print("API key with name apiKey already exists. Delete the key "
              " with name apiKey and try again.")
        exit(1)

    api_key = json.loads(json.dumps(resp.json()))['key']

    return api_key


def configure_grafana(eflow_ip: str, json_path: str, grafana_ip: str):

    head = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    #update datasource with eflow vm ip
    datasource_paths = {
        os.path.join(json_path, 'influx_datasource.yml')
    }
    for path in datasource_paths:
        with open(path, 'r') as source_file:
            datasource = source_file.read()
            datasource = datasource.replace("EFLOWIP", eflow_ip)

        with open(path, 'w') as source_file:
            source_file.write(datasource)

    print("Grafana datasource file update with eflow vm ip.")

    time.sleep(10)
    # update dashboards with eflow vm ip
    with open(os.path.join(json_path, 'defect_dashboard_windows.json'), 'r') as d_file:
        dashboard_data = d_file.read()
        dashboard_data = dashboard_data.replace("EFLOWIP", eflow_ip)

    with open(os.path.join(json_path, 'defect_dashboard_windows.json'), 'w') as d_file:
        d_file.write(dashboard_data)

    with open(os.path.join(json_path, 'safety_dashboard_windows.json'), 'r') as d_file:
        dashboard_data = d_file.read()
        dashboard_data = dashboard_data.replace("EFLOWIP", eflow_ip)

    with open(os.path.join(json_path, 'safety_dashboard_windows.json'), 'w') as d_file:
        d_file.write(dashboard_data)

    print("Grafana dashboards updated with eflow vm ip.")


def update_telegraf(eflow_ip: str, config_path:str):
    """
    Update telegraf config

    :param eflow_ip: EFLOW VM IP
    :param config_path : Telegraf config file path
    """
    telegraf_conf = os.path.join(config_path, 'telegraf.conf')
    with open(telegraf_conf, 'r') as conf_file:
        conf_data=conf_file.read()
        conf_data = conf_data.replace('EFLOWIP', eflow_ip)

    # Write the file out again
    with open(telegraf_conf, 'w') as conf_file:
        conf_file.write(conf_data)


def main():
    """Main method"""
    args = argparser().parse_args()
    eflow_ip = args.eflow_ip

    grafana_ip = "127.0.0.1"
    json_path = ".\\"

    # configure dashboard and datasource in grafana
    configure_grafana(eflow_ip, json_path, grafana_ip)

    # configure telegraf config file
    update_telegraf(eflow_ip, json_path)

if __name__ == "__main__":
    main()
