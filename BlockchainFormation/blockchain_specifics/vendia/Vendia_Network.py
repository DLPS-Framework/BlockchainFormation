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
import subprocess

class Vendia_Network:

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

        config['node_indices'] = list(range(0, config['vm_count']))
        config['groups'] = [config['node_indices']]

        os.system(f"cp /home/user/vendia-share/bmw-example/registration.json {config['exp_dir']}")

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



        cdh_call = subprocess.Popen(["cdh get bc-exp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output, errors = cdh_call.communicate(input=reply)
        cdh_call.wait()
        print(output)
        print(errors)

        # os.system("cdh get bc-exp")

        reply = str(input("Input YK")).strip()