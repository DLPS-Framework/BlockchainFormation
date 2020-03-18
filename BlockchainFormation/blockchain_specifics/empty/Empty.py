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


class Empty:

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
