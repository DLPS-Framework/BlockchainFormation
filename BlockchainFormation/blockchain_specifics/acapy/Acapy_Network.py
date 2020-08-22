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


import hashlib
import json

from BlockchainFormation.utils.utils import *


class Acapy_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the acapy specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the acapy specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        # the indices of the blockchain nodes
        config['coordinator_indices'] = [0]
        config['agent_indices'] = list(range(1, config['vm_count']))

        for index, _ in enumerate(config['priv_ips']):
            # scp_clients[index].put("/media/sf_VM_Benchmarking/Aries-Cloud-Agent/cdk/components/ec2/aries_agent/deployment", "/home/ubuntu", recursive=True)
            scp_clients[index].put("/home/user/Downloads/deployment", "/home/ubuntu", recursive=True)
            scp_clients[index].put("/media/sf_VM_Benchmarking/aries-cloudagent", "/home/ubuntu", recursive=True)
            scp_clients[index].put("/media/sf_VM_Benchmarking/aries-test-framework", "/home/ubuntu", recursive=True)

            stdin, stdout, stderr = ssh_clients[index].exec_command("cd /home/ubuntu/aries-cloudagent "
                                                                    "&& python3 -m pip install . >> /home/ubuntu/aries-cloudagent/install.log 2>&1 "
                                                                    "&& python3 -m pip install -r requirements.txt >> /home/ubuntu/aries-cloudagent/install.log 2>&1" 
                                                                    "&& python3 -m pip install -r requirements.dev.txt >> /home/ubuntu/aries-cloudagent/install.log 2>&1"
                                                                    "&& python3 -m pip install -r requirements.indy.txt >> /home/ubuntu/aries-cloudagent/install.log 2>&1")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())




        logger.info("Acapy agent is running...")

    @staticmethod
    def restart(node_handler):
        """
        Restart Acapy Agents
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

        Acapy_Network.shutdown(config, logger, ssh_clients, scp_clients)
        Acapy_Network.startup(config, logger, ssh_clients, scp_clients)

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
        except Exception as e:
            logger.exception(e)
            logger.error("ERROR: Problem loading the given config file")

        network_config_file["client settings"] = {

            "ips": config["ips"],
            "exp_dir": config["exp_dir"]

        }

        try:
            network_config_file['launch_times'] = config['launch_times'],
            network_config_file['vpc_ids'] = config['vpc_ids']
            network_config_file['instance_ids'] = config['instance_ids']

        except Exception as e:
            logger.info("No vpc_ids and instance_ids available")

        logger.info("Attaching client config to parent network config now")
        logger.info(f"Target parent network: {config['client_settings']['target_network_conf']}")
        if config['public_ip']:
            network_config_file["client settings"]['public_ips'] = 'public_ips'

        # write network config back
        with open(f"{config['client_settings']['target_network_conf']}", 'w') as outfile:
            json.dump(network_config_file, outfile, default=datetimeconverter, indent=4)
