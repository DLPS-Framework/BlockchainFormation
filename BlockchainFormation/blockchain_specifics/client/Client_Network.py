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


class Client_Network:

    @staticmethod
    def shutdown(node_handler):
        pass

    @staticmethod
    def startup(node_handler):
        """
        Startup for the blockchain client option
        :param config:
        :param logger:
        :param ssh_clients:
        :param scp_clients:
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        if config["client_settings"]["target_network_conf"] is not None:
            # Attach client IPs to network conf
            Client_Network.attach_to_blockchain_conf(node_handler)

    @staticmethod
    def attach_to_blockchain_conf(node_handler):
        """
        Attach client settings to another config
        :param config:
        :param logger:
        :return:
        """

        config = node_handler.config
        logger = node_handler.logger

        try:
            with open(config["client_settings"]["target_network_conf"]) as json_file:
                network_config_file = json.load(json_file)
        except:
            logger.error("ERROR: Problem loading the given config file")

        network_config_file["client settings"] = {

            "ips": config["ips"],
            "exp_dir": config["exp_dir"],
            "aws_region": config["aws_region"],


        }

        try:
            network_config_file["client settings"]['launch_times'] = config['launch_times'],
            network_config_file["client settings"]['vpc_ids'] = config['vpc_ids']
            network_config_file["client settings"]['instance_ids'] = config['instance_ids']
            network_config_file["client settings"]['ips'] = config["ips"]
            network_config_file["client settings"]['priv_ips'] = config['priv_ips']

        except Exception as e:
            logger.info("No vpc_ids and instance_ids available")

        logger.info("Attaching client config to parent network config now")
        logger.info(f"Target parent network: {config['client_settings']['target_network_conf']}")
        if config['public_ip']:
            network_config_file["client settings"]['pub_ips'] = config["pub_ips"]

        # write network config back
        with open(f"{config['client_settings']['target_network_conf']}", 'w') as outfile:
            json.dump(network_config_file, outfile, default=datetimeconverter, indent=4)
