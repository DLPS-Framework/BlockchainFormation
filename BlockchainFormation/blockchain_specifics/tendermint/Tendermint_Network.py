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
import os
import time

from BlockchainFormation.utils.utils import *


class Tendermint_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the tendermint specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the tendermint specific startup script
        :return:
        """

        # https://docs.tendermint.com/master/app-dev/getting-started.html
        # https://docs.tendermint.com/master/tendermint-core/using-tendermint.html#
        # https://irisnet.org/docs/daemon/local-testnet.html#multiple-nodes-testnet

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        dir_name = os.path.dirname(os.path.realpath(__file__))

        # the indices of the blockchain nodes
        config['node_indices'] = list(range(0, config['vm_count']))
        config['groups'] = [config['node_indices']]

        # Creating docker swarm
        logger.info("Preparing & starting docker swarm")

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm init")
        out = stdout.readlines()
        # for index, _ in enumerate(out):
        #     logger.debug(out[index].replace("\n", ""))

        # logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm join-token manager")
        out = stdout.readlines()
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))
        join_command = out[2].replace("    ", "").replace("\n", "")

        for index, _ in enumerate(config['priv_ips']):

            if index != 0:
                stdin, stdout, stderr = ssh_clients[index].exec_command("sudo " + join_command)
                out = stdout.readlines()
                # logger.debug(out)
                # logger.debug("".join(stderr.readlines()))

        config['join_command'] = "sudo " + join_command
        # Name of the swarm network
        my_net = "my-net"
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo docker network create --subnet 10.10.0.0/16 --attachable --driver overlay {my_net}")
        out = stdout.readlines()
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))
        network = out[0].replace("\n", "")

        logger.info("Testing whether setup was successful")
        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker node ls")
        out = stdout.readlines()
        for index, _ in enumerate(out):
            logger.debug(out[index].replace("\n", ""))

        logger.debug("".join(stderr.readlines()))
        if len(out) == len(config['priv_ips']) + 1:
            logger.info("Docker swarm started successfully")
        else:
            logger.info("Docker swarm setup was not successful")
            sys.exit("Fatal error when performing docker swarm setup")

        genesis = {
            "genesis_time": "2020-08-10T19:56:34.518443393Z",
            "chain_id": "10",
            "consensus_params": {
                "block": {
                    "max_bytes": "22020096",
                    "max_gas": "-1",
                    "time_iota_ms": "1000"
                },
                "evidence": {
                    "max_age_num_blocks": "100000",
                    "max_age_duration": "172800000000000",
                    "max_num": 50,
                    "proof_trial_period": "50000"
                },
                "validator": {
                    "pub_key_types": [
                        "ed25519"
                    ]
                },
                "version": {}
            },
            "validators": [
            ],
            "app_hash": ""
        }

        logger.info(f"Genesis: {genesis}")
        priv_keys = []
        pub_keys = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && tendermint init")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())

            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && tendermint gen_validator | jq -r '.Key' > ~/.tendermint/config/priv_validator_key.json")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())

            stdin, stdout, stderr = ssh_clients[index].exec_command(f"cat ~/.tendermint/config/priv_validator_key.json | jq -r '.pub_key' | jq -r '.value'")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stderr.readlines())

            pub_keys.append(out[0].replace("\n", ""))

            stdin, stdout, stderr = ssh_clients[index].exec_command(f"cat ~/.tendermint/config/priv_validator_key.json | jq -r '.priv_key' | jq -r '.value'")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stderr.readlines())

            priv_keys.append(out[0].replace("\n", ""))

            genesis["validators"].append(
            {
                "pub_key": {
                    "value": pub_keys[index],
                    "type": "tendermint/PubKeyEd25519"
                },
                "power": "10",
                "name": ""
            })

        logger.info(f"Pub_keys: {pub_keys}")
        logger.info(f"Priv_keys: {priv_keys}")
        logger.info(f"Genesis: {genesis}")

        with open(f"{config['exp_dir']}/setup/genesis.json", 'w+') as outfile:
            json.dump(genesis, outfile, indent=4)

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].put(f"{config['exp_dir']}/setup/genesis.json", "~/.tendermint/config/genesis.json")

        node_ids = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(". ~/.profile && tendermint show_node_id")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stdout.readlines())

            node_ids.append(out[0].replace("\n", ""))

        logger.info(f"Node_ids: {node_ids}")

        for index, _ in enumerate(config['priv_ips']):
            seed_string = "--p2p.seeds \""
            for index2, _ in enumerate(config['priv_ips']):
                if index2 != index:
                    if seed_string != "--p2p.seeds \"":
                        seed_string = seed_string + ","

                    seed_string = seed_string + f"{node_ids[index2]}@{config['priv_ips'][index2]}:26656"

            seed_string = seed_string + "\""
            print(f"Seed_string: {seed_string}")

            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f". ~/.profile && tendermint node --consensus.create_empty_blocks=false --proxy_app=kvstore {seed_string} >> ~/node.log")
            # --rpc.laddr \"tcp://{config['priv_ips']['index']}:26657\" --rpc.unsafe

            logger.info(f". ~/.profile && tendermint node --proxy_app=kvstore {seed_string} >> ~/node.log")

        time.sleep(10)

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].put(f"{dir_name}/setup", "/home/ubuntu", recursive=True)

        logger.info("Installing npm packages")
        for index, _ in enumerate(config['priv_ips']):
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(cd setup && . ~/.profile && npm install >> /home/ubuntu/setup/install.log && echo Success >> /home/ubuntu/setup/install.log)")

        status_flags = wait_till_done(config, ssh_clients, config['ips'], 180, 10, "/home/ubuntu/setup/install.log", "Success", 30, logger)
        # if False in status_flags:
        # raise Exception("Installation failed")

        logger.info("Starting the Server")
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command("echo '{\n    \"ip\": \"" + f"{config['priv_ips'][index]}" + "\"\n}' >> ~/setup/config.json")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(source /home/ubuntu/.profile && cd setup && node server.js >> /home/ubuntu/server.log)")



    @staticmethod
    def restart(node_handler):
        """
        Runs the tendermint specific restart script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients
