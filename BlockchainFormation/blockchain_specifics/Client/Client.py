#  Copyright 2020 ChainLab
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.



import json
from BlockchainFormation.utils.utils import *


def client_startup(config, logger, ssh_clients, scp_clients):
    """
    Startup for the blockchain client option
    :param config:
    :param logger:
    :param ssh_clients:
    :param scp_clients:
    :return:
    """

    if config["client_settings"]["target_network_conf"] is not None:
        # Attach client IPs to network conf
        attach_to_blockchain_conf(config, logger)


def attach_to_blockchain_conf(config, logger):
    """
    Attach client settings to another config
    :param config:
    :param logger:
    :return:
    """
    try:
        with open(config["client_settings"]["target_network_conf"]) as json_file:
            network_config_file = json.load(json_file)
    except:
        logger.error("ERROR: Problem loading the given config file")

    network_config_file["client settings"] = {

        "ips": config["ips"],
        "vpc_ids": config["vpc_ids"],
        "instance_ids": config["instance_ids"],
        "launch_times": config["launch_times"],
        "exp_dir": config["exp_dir"]

    }
    logger.info("Attaching client config to parent network config now")
    logger.info(f"Target parent network: {config['client_settings']['target_network_conf']}")
    if config['public_ip']:
        network_config_file["client settings"]['public_ips'] = 'public_ips'

    # write network config back
    with open(f"{config['client_settings']['target_network_conf']}", 'w') as outfile:
        json.dump(network_config_file, outfile, default=datetimeconverter, indent=4)