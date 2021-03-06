#  Copyright 2021 ChainLab
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

from BlockchainFormation.utils.utils import *


class Indy_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the indy specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        for index, _ in enumerate(config['priv_ips']):
            logger.info("Killing all indy processes")

            stdin, stdout, stderr = ssh_clients[index].exec_command("screen -list | grep Detached | cut -d. -f1 | awk '{print $1}' | xargs kill")
            wait_and_log(stdout, stderr)

            time.sleep(5)

            logger.debug("Deleting ledger and wallet data")

            stdin, stdout, stderr = ssh_clients[index].exec_command("sudo rm -r /home/ubuntu/.indy_client /data/indy /var/log/indy")
            wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[index].exec_command("sudo mkdir /var/log/indy /data/indy /data/indy/backup /data/indy/plugins; sudo chown -R ubuntu:ubuntu /var/log/indy/ /data/indy/ /etc/indy/")
            wait_and_log(stdout, stderr)

    @staticmethod
    def startup(node_handler):
        """
        Runs the indy specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

        # the indices of the blockchain nodes
        config['node_indices'] = list(range(0, config['vm_count']))
        config['groups'] = [config['node_indices']]

        node_names = []
        node_seeds = []
        ips_string = ""
        node_nums = ""

        for node, _ in enumerate(config['priv_ips']):
            if config['indy_settings']['public_network'] == 1:
                ip = config['pub_ips'][node]
            else:
                ip = config['priv_ips'][node]

            node_names.append(f"Node{node + 1}")
            node_name = hashlib.md5(node_names[node].encode()).hexdigest()
            node_seeds.append(node_name)
            if ips_string != "":
                ips_string = ips_string + ","
            ips_string = ips_string + ip

            if node_nums != "":
                node_nums = node_nums + " "
            node_nums = node_nums + f"{node + 1}"

        logger.info(f"Node_names: {node_names}")
        logger.info(f"Node_nums: {node_nums}")
        logger.info(f"Ips_string: {ips_string}")

        port = 9700
        channels = []

        for node, _ in enumerate(config['priv_ips']):
            init_string = f"init_indy_keys --name {node_names[node]} --seed {node_seeds[node]}"
            logger.debug(f"{init_string}")
            stdin, stdout, stderr = ssh_clients[node].exec_command(f"{init_string} && echo \"{init_string}\" >> commands.txt")
            stdout.readlines()
            stderr.readlines()
            # wait_and_log(stdout, stderr)
            tx_string = f"generate_indy_pool_transactions --nodes {len(ssh_clients)} --clients {config['indy_settings']['clients']} --nodeNum {node + 1} --ips \'{ips_string}\' --network my-net"
            logger.debug(f"{tx_string}")
            stdin, stdout, stderr = ssh_clients[node].exec_command(f"{tx_string} && echo \"{tx_string}\" >> commands.txt")
            stdout.readlines()
            stderr.readlines()
            # wait_and_log(stdout, stderr)
            channel = ssh_clients[node].get_transport().open_session()
            channels.append(channel)
            start_string = f"screen -dmS indy-node start_indy_node {node_names[node]} 0.0.0.0 {port + 1} 0.0.0.0 {port + 2} -vv"
            logger.debug(f"{start_string}")
            channels[node].exec_command(f"{start_string} && echo \"{start_string}\" >> commands.txt")
            port = port + 2
            time.sleep(5)

        logger.info("Indy network is running...")

        logger.info("Getting pool transactions genesis")
        scp_clients[0].get("/data/indy/my-net/pool_transactions_genesis", f"{config['exp_dir']}")

    @staticmethod
    def restart(node_handler):
        """
        Restart Indy Network
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

        Indy_Network.shutdown(node_handler)
        Indy_Network.startup(node_handler)
