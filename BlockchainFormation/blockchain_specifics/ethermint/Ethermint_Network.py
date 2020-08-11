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


class Ethermint_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the ethermint specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the ethermint specific startup script
        :return:
        """

        # https://github.com/ChainSafe/ethermint-deploy/blob/master/web3/deploy_contract.js
        # https://ethereum.stackexchange.com/questions/19122/authentication-needed-password-or-unlock-error-when-trying-to-call-smart-cont/19123
        # https://docs.ethermint.zone/guides/truffle.html

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        dir_name = os.path.dirname(os.path.realpath(__file__))

        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && ethermintcli config keyring-backend test && ethermintcli config trust-node true")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())

        node_names = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && ethermintd init node{index} --chain-id=10 > ~/config.json 2>&1")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())
            node_names.append(f"node{index}")

        logger.info(f"Node_names: {node_names}")

        logger.info("Getting genesis")
        try:
            scp_clients[0].get("/home/ubuntu/.ethermintd/config/genesis.json", f"{config['exp_dir']}/setup/genesis.json")
        except Exception as e:
            logger.exception(e)

        keys = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && ethermintcli keys add mykeynode{index}") # <<< $'userpassword\nuserpassword' > ~/key.key 2>&1")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())
            keys.append(f"mykeynode{index}")

        logger.info(f"Keys: {keys}")

        accounts = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && echo 'userpassword' | ethermintcli keys show -a mykeynode{index}")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stderr.readlines())
            accounts.append(out[0].replace("\n", ""))

        logger.info(f"Accounts: {accounts}")

        for index, _ in enumerate(config['priv_ips']):
            for index2, _ in enumerate(config['priv_ips']):
                stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && ethermintd add-genesis-account {accounts[index2]} 1000000000stake,10000000000photon")
                logger.info(stdout.readlines())
                logger.info(stderr.readlines())

        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f". ~/.profile && ethermintd gentx --name mykeynode{index} --keyring-backend test") # <<< $'userpassword\nuserpassword\nuserpassword'")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())

        gentxsnames = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(". ~/.profile && cd ~/.ethermintd/config/gentx && ls")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stderr.readlines())
            gentxsnames.append(out[0].replace("\n", ""))

        logger.info(f"Gentxsnames: {gentxsnames}")

        gentxs = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command("cd ~/.ethermintd/config/gentx && cat *")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stderr.readlines())
            gentxs.append(out[0].replace("\n", ""))

        logger.info(f"Gentxs: {gentxs}")

        for index, _ in enumerate(config['priv_ips']):
            for index2, _ in enumerate(config['priv_ips']):
                if index != index2:
                    stdin, stdout, stderr = ssh_clients[index].exec_command(f"echo '{gentxs[index2]}' > ~/.ethermintd/config/gentx/{gentxsnames[index2]}")
                    logger.info(stdout.readlines())
                    logger.info(stderr.readlines())

                stdin, stdout, stderr = ssh_clients[index].exec_command(". ~/.profile && ethermintd collect-gentxs")
                logger.info(stdout.readlines())
                logger.info(stderr.readlines())

        scp_clients[0].get("/home/ubuntu/.ethermintd/config/genesis.json", f"{config['exp_dir']}/setup/genesis.json")

        for index, _ in enumerate(config['priv_ips']):
            if index != 0:
                stdin, stdout, stderr = ssh_clients[index].exec_command("rm /home/ubuntu/.ethermintd/config/genesis.json")
                logger.info(stdout.readlines())
                logger.info(stderr.readlines())

                scp_clients[index].put(f"{config['exp_dir']}/setup/genesis.json", "/home/ubuntu/.ethermintd/config/genesis.json")

                stdin, stdout, stderr = ssh_clients[index].exec_command(". ~/.profile && ethermintd validate-genesis")
                logger.info(stdout.readlines())
                logger.info(stderr.readlines())

        for index, _ in enumerate(config['priv_ips']):
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(". ~/.profile && ethermintd start >> ~/node.log")

        for index, _ in enumerate(config['priv_ips']):
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f". ~/.profile && ethermintcli rest-server --laddr 'tcp://{config['priv_ips'][index]}:8545' --unlock-key mykeynode{index}  --chain-id 10 >> rest.log")

        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(
                "curl -X POST --data '{\"jsonrpc\":\"2.0\",\"method\":\"eth_accounts\",\"params\":[],\"id\":1}' -H \"Content-Type: application/json\" "
                + f"{config['priv_ips'][index]}:8545")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())


    @staticmethod
    def restart(node_handler):
        """
        Runs the ethermint specific restart script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients
