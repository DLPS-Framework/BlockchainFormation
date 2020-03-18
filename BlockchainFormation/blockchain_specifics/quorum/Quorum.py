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
import rlp

from BlockchainFormation.utils.utils import *

class Quorum:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the quorum specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        logger.info("Getting quorum logs from the network")
        boo = True

        for index, ip in enumerate(config['ips']):

            os.mkdir(f"{config['exp_dir']}/quorum_logs")
            os.mkdir(f"{config['exp_dir']}/tessera_logs")

            try:
                scp_clients[index].get("/home/ubuntu/node.log", f"{config['exp_dir']}/quorum_logs/quorum_log_node_{index}.log")
                scp_clients[index].get("/home/ubuntu/tessera.log", f"{config['exp_dir']}/tessera_logs/tessera_log_node_{index}.log")
            except Exception as e:
                logger.debug(e)
                logger.info(f"Not all logs available on {ip}")
                boo = False

        if boo is True:
            logger.info("All logs successfully stored")

    @staticmethod
    def startup(node_handler):
        """
        Runs the geth specific startup script
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

        # for saving the enodes and addresses of the nodes resp. wallets (each node has one wallet at the moment)
        enodes = []
        addresses = []

        logger.info("Generating the enode on each node, storing it in enodes, and deriving an account (the coinbase account)")
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command("(bootnode --genkey=nodekey "
                                                                    "&& mkdir /data/nodes/new-node-1 "
                                                                    "&& mv nodekey /data/nodes/new-node-1/nodekey)")
            wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[index].exec_command("bootnode --nodekey=/data/nodes/new-node-1/nodekey --writeaddress")
            out = stdout.readlines()
            enode = out[0].replace("\n", "").replace("]", "").replace("[", "")
            enodes.append(enode)
            logger.debug(f"Enode on node {index}: {enode}")

            stdin, stdout, stderr = ssh_clients[index].exec_command("geth account import /data/nodes/new-node-1/nodekey "
                                                                    "--datadir /data/nodes/new-node-1 "
                                                                    "--password /data/nodes/pwd "
                                                                    "> /data/nodes/address "
                                                                    ""
                                                                    "&& sed -i -e 's/Address: //g' /data/nodes/address && sed -i -e 's/{//g' /data/nodes/address "
                                                                    "&& sed -i -e 's/}//g' /data/nodes/address")
            wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[index].exec_command("cat /data/nodes/address")
            out = stdout.readlines()
            address = out[0].replace("\n", "")
            addresses.append(address)
            logger.debug(f"Address (coinbase) on node {index}: {address}")

        config['enodes'] = enodes
        config['addresses'] = addresses

        logger.info("Replacing the genesis_raw.json on each node by genesis.json where the coinbase of the first node has some ether")
        for index, _ in enumerate(config['priv_ips']):

            logger.debug("Removing the genesis_raw.json which is not relevant for the consensus")
            if config['quorum_settings']['consensus'].upper() == "IBFT":
                stdin, stdout, stderr = ssh_clients[index].exec_command("rm /data/genesis_raw_raft.json "
                                                                        "&& mv /data/genesis_raw_istanbul.json /data/genesis_raw.json")
                wait_and_log(stdout, stderr)

            else:
                stdin, stdout, stderr = ssh_clients[index].exec_command("rm /data/genesis_raw_istanbul.json "
                                                                        "&& mv /data/genesis_raw_raft.json /data/genesis_raw.json")
                wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[index].exec_command("(sed -i -e 's/substitute_address/'" + f"'{addresses[0]}'" + "'/g' /data/genesis_raw.json "
                                                                                                                                 "&& mv /data/genesis_raw.json /data/nodes/genesis.json)")
            stdout.readlines()
            wait_and_log(stdout, stderr)

        if config['quorum_settings']['consensus'].upper() == "IBFT":
            logger.info("Creating extra data for the istanbul genesis")
            for index, _ in enumerate(config['priv_ips']):

                old_string = "f841"
                new_string = "b841"
                for i in range(0, 65):
                    old_string = old_string + "80"
                    new_string = new_string + "00"

                vanity = "0x0000000000000000000000000000000000000000000000000000000000000000"
                seal = []
                for i in range(0, 65):
                    seal.append(0x00)

                committed_seal = []

                validators = []
                for address in addresses:
                    validators.append(int("0x" + address, 16))

                extra_data = vanity + rlp.encode([validators, seal, committed_seal]).hex()

                extra_data = extra_data.replace(old_string, new_string)

                stdin, stdout, stderr = ssh_clients[index].exec_command("sed -i -e 's/substitute_extra_data/'" + f"'{extra_data}'" + "'/g' /data/nodes/genesis.json")
                wait_and_log(stdout, stderr)

        logger.info("Generating static-nodes on each node and initializing the genesis block afterwards")
        if config['quorum_settings']['consensus'].upper() == "IBFT":
            port_string = "30300"
            raftport_string = ""

        else:
            port_string = "21000"
            raftport_string = "&raftport=50000"

        for index1, _ in enumerate(config['priv_ips']):

            stdin, stdout, stderr = ssh_clients[index1].exec_command("echo '[' > /data/nodes/new-node-1/static-nodes.json")
            wait_and_log(stdout, stderr)

            if config['quorum_settings']['consensus'].upper() == "IBFT":
                limit = len(config['priv_ips'])

            else:
                limit = index1 + 1

            for index2, ip2 in enumerate(config['priv_ips'][0:limit]):
                if index2 < limit - 1:
                    string = "echo '  " + '\"' + "enode://" + f"{enodes[index2]}" + "@" + f"{ip2}" + f":{port_string}?discport=0{raftport_string}'" + '\\",' + \
                             " >> /data/nodes/new-node-1/static-nodes.json"
                    stdin, stdout, stderr = ssh_clients[index1].exec_command(string)
                    wait_and_log(stdout, stderr)
                else:
                    string = "echo '  " + '\"' + "enode://" + f"{enodes[index2]}" + "@" + f"{ip2}" + f":{port_string}?discport=0{raftport_string}'" + '\\"' + \
                             " >> /data/nodes/new-node-1/static-nodes.json"
                    stdin, stdout, stderr = ssh_clients[index1].exec_command(string)
                    wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[index1].exec_command("(echo ']' >> /data/nodes/new-node-1/static-nodes.json "
                                                                     "&& geth --datadir /data/nodes/new-node-1 init /data/nodes/genesis.json)")
            wait_and_log(stdout, stderr)

        logger.info("Starting tessera_nodes")
        tessera_public_keys = Quorum.start_tessera(config, ssh_clients, logger)
        config['tessera_public_keys'] = tessera_public_keys

        logger.info("Starting quorum nodes")
        Quorum.start_network(config, ssh_clients, logger)

    @staticmethod
    def start_tessera(config, ssh_clients, logger):
        # for saving the public and private keys of the tessera nodes (enclaves)
        tessera_public_keys = []

        logger.info("Getting tessera-data from each node and create config-file for tessera on each node")
        for index1, ip1 in enumerate(config['priv_ips']):

            # getting tessera public and private keys (which have been generated during bootstrapping)
            # and store them in the corresponding arrays <tessera_public_keys> resp. <tessera_private_keys>
            stdin, stdout, stderr = ssh_clients[index1].exec_command("cat /data/qdata/tm/tm.pub")
            out = stdout.readlines()
            tessera_public_key = out[0].replace("\n", "")
            tessera_public_keys.append(tessera_public_key)
            logger.debug(f"Tessera public key on node {index1}: {tessera_public_key}")

            stdin, stdout, stderr = ssh_clients[index1].exec_command("cat /data/qdata/tm/tm.key")
            out = stdout.readlines()
            tessera_private_key = out[3].replace('      "bytes" : ', "").replace('\n', "")
            logger.debug(f"Tessera private key on node {index1}: {tessera_private_key}")

            # building peer string which is then inserted to config_raw.json, which contains all tessera-specific information,
            # in particular the tessera-nodes which will participate in the (private) quorum network
            peer_string = '\\"peer\\":\ ['

            for index2, ip2 in enumerate(config['priv_ips']):

                if index2 < len(config['priv_ips']) - 1:
                    peer_string = peer_string + '{\\"url\\":\ \\"http://' + f'{ip2}' + ':9000\\"},'
                else:
                    peer_string = peer_string + '{\\"url\\":\ \\"http://' + f'{ip2}' + ':9000\\"}'

            peer_string = peer_string + "],"

            # Specifying missing data in config_raw.json and store the result in config.json
            stdin, stdout, stderr = ssh_clients[index1].exec_command(f"(sed -i -e s#substitute_ip#{ip1}#g /data/config_raw.json "
                                                                     f"&& sed -i -e s#substitute_public_key#{tessera_public_keys[index1]}#g /data/config_raw.json "
                                                                     f"&& sed -i -e s#substitute_private_key#{tessera_private_key}#g /data/config_raw.json && "
                                                                     f"sed -i -e s#substitute_peers#" + peer_string + "#g /data/config_raw.json "
                                                                                                                      f"&& mv /data/config_raw.json /data/qdata/tm/config.json)")
            wait_and_log(stdout, stderr)

            # logger.debug(f"Starting tessera on node {index1}")
            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("java -jar /data/tessera/tessera-app-0.10.0-app.jar -configfile /data/qdata/tm/config.json >> /home/ubuntu/tessera.log 2>&1")

        logger.info("Waiting until all tessera nodes have started")
        status_flags = wait_till_done(config, ssh_clients, config['ips'], 60, 10, '/data/qdata/tm/tm.ipc', False, 10, logger)
        if False in status_flags:
            raise Exception("At least one tessera node did not start properly")

        return tessera_public_keys

    @staticmethod
    def start_network_attempt(config, ssh_clients, logger):
        for index, ip in enumerate(config['priv_ips']):

            if index == 0:
                Quorum.start_node(config, ssh_clients, index, logger)
                time.sleep(5)

            else:

                if config['quorum_settings']['consensus'].upper() == "IBFT":
                    pass
                else:
                    Quorum.add_node(config, ssh_clients, index, logger)
                    time.sleep(2)

                Quorum.start_node(config, ssh_clients, index, logger)
                time.sleep(2)

        status_flags = Quorum.check_network(config, ssh_clients, logger)

        if False in status_flags:
            logger.info("Restart was not successful")
            try:
                logger.info("Restarting failed VMs")
                for node in np.where(status_flags == False):
                    Quorum.restart_node(config, ssh_clients, node, logger)

                status_flags = Quorum.check_network(config, ssh_clients, logger)

            except Exception as e:
                logger.exception(e)
                pass

        return status_flags

    @staticmethod
    def start_network(config, ssh_clients, logger):
        status_flags = Quorum.start_network_attempt(config, ssh_clients, logger)

        if False in status_flags:
            logger.info("Making a complete restart since it was not successful")

        retries = 0
        while False in status_flags and retries < 3:
            logger.info(f"Retry {retries + 1} out of 3")
            retries = retries + 1

            Quorum.kill_network(config, ssh_clients, logger)
            status_flags = Quorum.start_network_attempt(config, ssh_clients, logger)

        if False in status_flags:
            logger.error("Quorum network did not start successfully")
            raise Exception("Quorum network setup failed")

        logger.info("                                ")
        logger.info("================================")
        logger.info("Quorum network is running now...")
        logger.info("================================")
        logger.info("                                ")

        Quorum.unlock_network(config, ssh_clients, logger)

    @staticmethod
    def start_node(config, ssh_clients, node, logger):
        # making a substring with the geth-specific settings
        string_geth_settings = ""
        for key in config['quorum_settings']:
            if key not in ["private_fors", "consensus", "istanbul_blockperiod", "istanbul_minerthreads", "raft_blocktime"]:
                value = config['quorum_settings'][f"{key}"]
                string_geth_settings = string_geth_settings + f" --{key} {value}"

        logger.debug(f" --> Starting node {node} ...")
        channel = ssh_clients[node].get_transport().open_session()

        if config['quorum_settings']['consensus'].upper() == "IBFT":
            channel.exec_command(f"PRIVATE_CONFIG=/data/qdata/tm/tm.ipc geth "
                                 f"--datadir /data/nodes/new-node-1 "
                                 f"--nodiscover "
                                 f"--istanbul.blockperiod {config['quorum_settings']['istanbul_blockperiod']} "
                                 f"--maxpeers {config['vm_count']} "
                                 f"--syncmode full "
                                 f"--mine "
                                 f"--minerthreads {config['quorum_settings']['istanbul_minerthreads']} "
                                 f"--verbosity 5 "
                                 f"--networkid 10 "
                                 f"--rpc "
                                 f"--rpcaddr 0.0.0.0 "
                                 f"--rpcport 22000 "
                                 f"--rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,istanbul "
                                 f"--emitcheckpoints "
                                 f"--port 30300 "
                                 f"--nat=extip:{config['priv_ips'][node]}{string_geth_settings} "
                                 f">> /home/ubuntu/node.log 2>&1")

        else:
            if node == 0:
                channel.exec_command(f"PRIVATE_CONFIG=/data/qdata/tm/tm.ipc geth "
                                     f"--datadir /data/nodes/new-node-1 "
                                     f"--nodiscover "
                                     f"--verbosity 5 "
                                     f"--networkid 31337 "
                                     f"--raft "
                                     f"--raftblocktime {config['quorum_settings']['raft_blocktime']} "
                                     f"--maxpeers {config['vm_count']} "
                                     f"--raftport 50000 "
                                     f"--rpc --rpcaddr 0.0.0.0 "
                                     f"--rpcport 22000 "
                                     f"--rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft "
                                     f"--emitcheckpoints "
                                     f"--port 21000 "
                                     f"--nat=extip:{config['priv_ips'][node]}{string_geth_settings} "
                                     f">> /home/ubuntu/node.log 2>&1")
            else:
                channel.exec_command(f"PRIVATE_CONFIG=/data/qdata/tm/tm.ipc geth "
                                     f"--datadir /data/nodes/new-node-1 "
                                     f"--nodiscover "
                                     f"--verbosity 5 "
                                     f"--networkid 31337 "
                                     f"--raft "
                                     f"--raftblocktime {config['quorum_settings']['raft_blocktime']} "
                                     f"--maxpeers {config['vm_count']} "
                                     f"--raftport 50000 "
                                     f"--raftjoinexisting {node + 1} "
                                     f"--rpc "
                                     f"--rpcaddr 0.0.0.0 "
                                     f"--rpcport 22000 "
                                     f"--rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft "
                                     f"--emitcheckpoints "
                                     f"--port 21000 "
                                     f"--nat=extip:{config['priv_ips'][node]}{string_geth_settings} "
                                     f">> /home/ubuntu/node.log 2>&1")

    @staticmethod
    def add_node(config, ssh_clients, node, logger):
        logger.debug(f" --> Adding node {node} to raft on node {0} ...")
        stdin, stdout, stderr = ssh_clients[0].exec_command("geth --exec " +
                                                            '\"' + "raft.addPeer('enode://" + f"{config['enodes'][node]}" + "@" + f"{config['priv_ips'][node]}" + ":21000?discport=0&raftport=50000')" + '\"' +
                                                            " attach /data/nodes/new-node-1/geth.ipc")
        out = stdout.readlines()
        raft_id = out[0].replace("\x1b[0m\r\n", "").replace("\x1b[31m", "").replace("\n", "")
        logger.debug(f"raftID of node {node}: {raft_id}")

    @staticmethod
    def unlock_node(config, ssh_clients, node, logger):
        logger.debug(f" --> Unlocking node {node}")
        stdin, stdout, stderr = ssh_clients[node].exec_command("geth --exec eth.accounts attach /data/nodes/new-node-1/geth.ipc")
        out = stdout.readlines()
        sender = out[0].replace("\n", "").replace("[", "").replace("]", "")
        stdin, stdout, stderr = ssh_clients[node].exec_command("geth --exec " +
                                                               "\'" + f"personal.unlockAccount({sender}, " + '\"' + "user" + '\"' + ", 0)" + "\'" +
                                                               " attach /data/nodes/new-node-1/geth.ipc")
        out = stdout.readlines()
        if out[0].replace("\n", "") != "true":
            logger.info(f"Something went wrong on unlocking on node {node} on IP {config['ips']}")
            logger.debug(out)
            logger.debug(f"stderr: {stderr.readlines()}")

    @staticmethod
    def unlock_network(config, ssh_clients, logger):
        logger.info("Unlocking all accounts forever")
        for node, _ in enumerate(config['priv_ips']):
            Quorum.unlock_node(config, ssh_clients, node, logger)

    @staticmethod
    def check_network(config, ssh_clients, logger):
        """
        Check network Status
        :param config:
        :param ssh_clients:
        :param logger:
        :return:
        """

        status_flags = np.zeros(config['vm_count'], dtype=bool)
        timer = 0
        while False in status_flags and timer < 3:
            time.sleep(10)
            timer += 1
            logger.info(f" --> Waited {timer * 10} seconds so far, {30 - timer * 10} seconds left before abort (it usually takes around 10 seconds)")
            for index, ip in enumerate(config['ips']):

                if status_flags[index] == False:
                    try:
                        stdin, stdout, stderr = ssh_clients[index].exec_command("geth --exec " +
                                                                                '\"' + "admin.peers.length" + '\"' +
                                                                                " attach /data/nodes/new-node-1/geth.ipc")
                        out = stdout.readlines()

                        nr = int(out[0].replace("\n", ""))
                        if nr == len(config['priv_ips']) - 1:
                            logger.info(f"Node {index} on IP {ip} is fully connected")
                            status_flags[index] = True
                        else:
                            logger.info(f"Node {index} on IP {ip} is not yet fully connected (expected: {len(config['priv_ips']) - 1}, actual: {nr} ")
                    except Exception as e:
                        logger.exception(e)
                        logger.info(f"Node {index} might not have started at all - retrying though")

        if False in status_flags:
            try:
                logger.error(f"Failed Quorum nodes: {[config['priv_ips'][x] for x in np.where(status_flags is not True)]}")
            except:
                pass
            logger.error('Quorum network start was not successful')

        return status_flags

    @staticmethod
    def kill_node(ssh_clients, node, logger):
        """
        Shut down single geth node
        :param ssh_clients:
        :param node:
        :param logger:
        :return:
        """

        logger.debug(f" --> Shutting down and resetting node {node}")
        try:
            stdin, stdout, stderr = ssh_clients[node].exec_command("pidof geth")
            pid = stdout.readlines()[0].replace("\n", "")
            stdin, stdout, stderr = ssh_clients[node].exec_command(f"kill {pid}")
            stdout.readlines()
        except:
            logger.info(f"It seems that geth on node {node} is already killed")
            logger.info(f"Checking this")
            stdin, stdout, stderr = ssh_clients[node].exec_command("ps aux | grep geth")
            logger.info(f"stdout for ps aux | grep geth: {stdout.readlines()}")
            logger.info(f"stderr for ps aux | grep geth: {stderr.readlines()}")

            # checking whether the other geth-files are deleted
            stdin, stdout, stderr = ssh_clients[node].exec_command("ls /data/nodes/new-node-1")
            logger.info(f"Files in /nodes/new-node-1: {stdout.readlines}")
            logger.debug(stdout.readlines())

            # deleting the remaining geth-related files
            logger.info("Deleting relevant files")
            stdin, stdout, stderr = ssh_clients[node].exec_command("rm geth.ipc; rm -r quorum-raft-state; rm -r raft-snap; rm -r raft-wal")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

        # Clearing the tx-pool
        stdin, stdout, stderr = ssh_clients[node].exec_command("rm /data/nodes/new-node-1/geth/transactions.rlp")
        stdout.readlines()

    @staticmethod
    def kill_network(config, ssh_clients, logger):
        """
        Shut network down
        :param config:
        :param ssh_clients:
        :param logger:
        :return:
        """

        logger.info("Killing geth on all nodes")
        for node, _ in enumerate(config['priv_ips']):
            Quorum.kill_node(ssh_clients, node, logger)

    @staticmethod
    def restart_node(config, ssh_clients, node, logger):
        """
        Start up geth on all nodes
        :param config:
        :param ssh_clients:
        :param node:
        :param logger:
        :return:
        """

        Quorum.kill_node(ssh_clients, node, logger)
        Quorum.start_node(config, ssh_clients, node, logger)
        time.sleep(10)
        Quorum.unlock_node(config, ssh_clients, node, logger)

    @staticmethod
    def restart(node_handler):
        """
        Kills the network and Restarts its
        :param config:
        :param ssh_clients:
        :param logger:
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        Quorum.kill_network(config, ssh_clients, logger)
        Quorum.start_network(config, ssh_clients, logger)
