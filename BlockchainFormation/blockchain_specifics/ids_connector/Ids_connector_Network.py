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

import os

class Ids_connector_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the emtpy specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the empty specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        dir_name = os.path.dirname(os.path.realpath(__file__))

        os.system(f"cp {dir_name}/setup/docker-compose.yml {config['exp_dir']}/setup/docker-compose.yml")

        scp_clients[0].put(f"{config['exp_dir']}/setup/docker-compose.yml", "/home/ubuntu/DataspaceConnector/docker-compose.yml")

        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("cd ~/DataspaceConnector && docker-compose up >> /home/ubuntu/connector.log 2>&1")

    @staticmethod
    def restart(node_handler):
        """
        Runs the empty specific restart script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients
