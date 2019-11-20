#  Copyright 2019  ChainLab
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
import time
import numpy as np
from BlockchainFormation.utils.utils import *


def quorum_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the quorum specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['priv_ips']):

        scp_clients[index].get("/home/ubuntu/node.log", f"{config['exp_dir']}/quorum_logs/quorum_log_node_{index}.log")
        scp_clients[index].get("/home/ubuntu/tessera.log", f"{config['exp_dir']}/tessera_logs/tessera_log_node_{index}.log")
        scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


def quorum_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """

    # the indices of the blockchain nodes
    config['node_indices'] = list(range(0, config['vm_count']))

    logger.info("Creating directories for saving data and logs locally")
    os.mkdir((f"{config['exp_dir']}/quorum_logs"))
    os.mkdir((f"{config['exp_dir']}/tessera_logs"))

    # for saving the enodes and addresses of the nodes resp. wallets (each node has one wallet at the moment)
    addresses = []
    enodes = []

    logger.info("Getting the addresses of each node's wallet (which have been generated during bootstrapping) and store it in the corresponding array <addresses>")
    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("cat /home/ubuntu/nodes/address")
        out = stdout.readlines()
        addresses.append(out[0].replace("\n", ""))
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))

    logger.info("Replacing the genesis_raw.json on each node by genesis_raw where the first two nodes have some ether")
    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("(sed -i -e 's/substitute_address/'" + f"'{addresses[0]}'" + "'/g' /home/ubuntu/genesis_raw.json && mv /home/ubuntu/genesis_raw.json /home/ubuntu/nodes/genesis.json)")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

    config['addresses'] = addresses

    logger.info("Generating the enode on each node and storing it in enodes")
    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("(bootnode --genkey=nodekey && mv nodekey /home/ubuntu/nodes/new-node-1/nodekey)")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index].exec_command("bootnode --nodekey=/home/ubuntu/nodes/new-node-1/nodekey --writeaddress")
        out = stdout.readlines()
        enodes.append(out[0].replace("\n", "").replace("]", "").replace("[", ""))
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))

    config['enodes'] = enodes

    logger.info("Generating static-nodes on each node and initialize the genesis block afterwards")
    for index1, _ in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index1].exec_command("echo '[' > /home/ubuntu/nodes/new-node-1/static-nodes.json")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

        for index2, ip2 in enumerate(config['priv_ips'][0:index1 + 1]):
            if (index2 < index1):
                string = "echo '  " + '\"' + "enode://" + f"{enodes[index2]}" + "@" + f"{ip2}" + ":21000?discport=0&raftport=50000'" + '\\",' + " >> /home/ubuntu/nodes/new-node-1/static-nodes.json"
                stdin, stdout, stderr = ssh_clients[index1].exec_command(string)
                stdout.readlines()
                # logger.debug("".join(stdout.readlines()))
                # logger.debug("".join(stderr.readlines()))
            else:
                string = "echo '  " + '\"' + "enode://" + f"{enodes[index2]}" + "@" + f"{ip2}" + ":21000?discport=0&raftport=50000'" + '\\"' + " >> /home/ubuntu/nodes/new-node-1/static-nodes.json"
                stdin, stdout, stderr = ssh_clients[index1].exec_command(string)
                stdout.readlines()
                # logger.debug("".join(stdout.readlines()))
                # logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("(echo ']' >> /home/ubuntu/nodes/new-node-1/static-nodes.json && geth --datadir /home/ubuntu/nodes/new-node-1 init /home/ubuntu/nodes/genesis.json)")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

    logger.info("Starting tessera_nodes")
    tessera_public_keys, tessera_private_keys = start_tessera(config, ssh_clients, logger)
    config['tessera_public_keys'] = tessera_public_keys
    config['tessera_private_keys'] = tessera_private_keys

    logger.info("Starting quorum nodes")
    start_network(config, ssh_clients, logger)

    logger.info("Getting logs from vms")
    boo = True
    for index, ip in enumerate(config['ips']):

        try:
            scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")
            scp_clients[index].get("/home/ubuntu/tessera.log", f"{config['exp_dir']}/tessera_logs/tessera_node{index}.log")
            scp_clients[index].get("/home/ubuntu/node.log", f"{config['exp_dir']}/quorum_logs/quorum_node{index}.log")
            logger.debug(f"Logs fetched successfully from {ip}")
        except:
            logger.info(f"Not all logs available on {ip}")
            boo = False

    if boo == True:
        logger.info("All logs successfully stored")


def start_tessera(config, ssh_clients, logger):

    # for saving the public and private keys of the tessera nodes (enclaves)
    tessera_public_keys = []
    tessera_private_keys = []

    logger.info("Getting tessera-data from each node and create config-file for tessera on each node")
    for index1, ip1 in enumerate(config['priv_ips']):

        # getting tessera public and private keys (which have been generated during bootstrapping) and store them in the corresponding arrays <tessera_public_keys> resp. <tessera_private_keys>
        stdin, stdout, stderr = ssh_clients[index1].exec_command("cat /home/ubuntu/qdata/tm/tm.pub")
        out = stdout.readlines()
        # logger.debug("".join(out))
        # logger.debug("".join(stderr.readlines()))
        tessera_public_keys.append(out[0].replace("\n", ""))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("cat /home/ubuntu/qdata/tm/tm.key")
        out = stdout.readlines()
        # logger.debug("".join(out))
        # logger.debug("".join(stderr.readlines()))
        tessera_private_keys.append(out[3].replace('      "bytes" : ', "").replace('\n', ""))

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
        stdin, stdout, stderr = ssh_clients[index1].exec_command(f"(sed -i -e s#substitute_ip#{ip1}#g /home/ubuntu/config_raw.json && sed -i -e s#substitute_public_key#{tessera_public_keys[index1]}#g /home/ubuntu/config_raw.json && sed -i -e s#substitute_private_key#{tessera_private_keys[index1]}#g /home/ubuntu/config_raw.json && sed -i -e s#substitute_peers#" + peer_string + "#g /home/ubuntu/config_raw.json && mv /home/ubuntu/config_raw.json /home/ubuntu/qdata/tm/config.json)")
        stdout.readlines()

        # logger.debug(f"Starting tessera on node {index1}")
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("java -jar tessera/tessera-app-0.10.0-app.jar -configfile qdata/tm/config.json >> tessera.log 2>&1")

    logger.info("Waiting until all tessera nodes have started")
    status_flags = wait_till_done(config, ssh_clients, config['ips'], 60, 10, '/home/ubuntu/qdata/tm/tm.ipc', False, 10, logger)
    if False in status_flags:
        raise Exception("At least one tessera node did not start properly")

    return tessera_public_keys, tessera_private_keys


def start_network(config, ssh_clients, logger):

    for index, ip in enumerate(config['priv_ips']):

        if index == 0:

            start_node(config, ssh_clients, index, logger)
            time.sleep(5)

        else:

            add_node(config, ssh_clients, index, logger)
            time.sleep(2)
            start_node(config, ssh_clients, index, logger)
            time.sleep(2)

    status_flags = check_network(config, ssh_clients, logger)

    if (False in status_flags):

        try:

            logger.info("Restarting failed VMs")
            for node in np.where(status_flags != True):

                restart_node(node)

            status_flags = check_network(config, ssh_clients, logger)

        except:
            pass


    retries = 0
    while (False in status_flags and retries < 3):
        retries = retries + 1

        status_flags = check_network(config, ssh_clients, logger)
        quorum_restart(config, ssh_clients, logger)

    if False in status_flags:
        logger.error("Quorum network did not start successfully")
        raise Exception("Quorum network setup failed")


    logger.info("")
    logger.info("================================")
    logger.info("Quorum network is running now...")
    logger.info("================================")
    logger.info("")

    unlock_network(config, ssh_clients, logger)


def start_node(config, ssh_clients, node, logger):

    # making a substring with the geth-specific settings
    string_geth_settings = ""
    for key in config['quorum_settings']:
        if key != "private_fors":
            value = config['quorum_settings'][f"{key}"]
            string_geth_settings = string_geth_settings + f" --{key} {value}"

    logger.debug(f" --> Starting node {node} ...")
    channel = ssh_clients[node].get_transport().open_session()

    if node == 0:
        channel.exec_command(f"PRIVATE_CONFIG=/home/ubuntu/qdata/tm/tm.ipc geth --datadir /home/ubuntu/nodes/new-node-1 --nodiscover --verbosity 5 --networkid 31337 --raft --maxpeers {config['vm_count']} --raftport 50000 --rpc --rpcaddr 0.0.0.0 --rpcport 22000 --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft --emitcheckpoints --port 21000 --nat=extip:{config['priv_ips'][node]}{string_geth_settings} >> node.log 2>&1")

    else:
        channel.exec_command(f"PRIVATE_CONFIG=/home/ubuntu/qdata/tm/tm.ipc geth --datadir /home/ubuntu/nodes/new-node-1 --nodiscover --verbosity 5 --networkid 31337 --raft --maxpeers {config['vm_count']} --raftport 50000 --raftjoinexisting {node+1} --rpc --rpcaddr 0.0.0.0 --rpcport 22000 --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft --emitcheckpoints --port 21000 --nat=extip:{config['priv_ips'][node]}{string_geth_settings} >> node.log 2>&1")


def add_node(config, ssh_clients, node, logger):

    logger.debug(f" --> Adding node {node} to raft on node {0} ...")
    stdin, stdout, stderr = ssh_clients[0].exec_command("geth --exec " + '\"' + "raft.addPeer('enode://" + f"{config['enodes'][node]}" + "@" + f"{config['priv_ips'][node]}" + ":21000?discport=0&raftport=50000')" + '\"' + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
    out = stdout.readlines()
    # logger.debug(out)
    # logger.debug("".join(stderr.readlines()))
    # raftID = out[0].replace("\x1b[0m\r\n", "").replace("\x1b[31m", "").replace("\n", "")
    # logger.info(f"raftID: {raftID}")


def unlock_node(config, ssh_clients, node, logger):

    logger.debug(f" --> Unlocking node {node}")
    stdin, stdout, stderr = ssh_clients[node].exec_command("geth --exec eth.accounts attach /home/ubuntu/nodes/new-node-1/geth.ipc")
    out = stdout.readlines()
    sender = out[0].replace("\n", "").replace("[", "").replace("]", "")
    stdin, stdout, stderr = ssh_clients[node].exec_command("geth --exec " + "\'" + f"personal.unlockAccount({sender}, " + '\"' + "user" + '\"' + ", 0)" + "\'" + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
    out = stdout.readlines()
    if out[0].replace("\n", "") != "true":
        logger.info(f"Something went wrong on unlocking on node {node} on IP {config['ips']}")
        logger.debug(out[0])


def unlock_network(config, ssh_clients, logger):

    logger.info("Unlocking all accounts forever")
    for node, _ in enumerate(config['priv_ips']):
        unlock_node(config, ssh_clients, node, logger)



def check_network(config, ssh_clients, logger):

    status_flags = np.zeros(config['vm_count'], dtype=bool)
    timer = 0
    while (False in status_flags and timer < 3):
        time.sleep(10)
        timer += 1
        logger.info(f" --> Waited {timer * 10} seconds so far, {30 - timer * 10} seconds left before abort (it usually takes around 10 seconds)")
        for index, ip in enumerate(config['ips']):

            if (status_flags[index] == False):
                try:
                    stdin, stdout, stderr = ssh_clients[index].exec_command("geth --exec " + '\"' + "admin.peers.length" + '\"' + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
                    out = stdout.readlines()
                except Exception as e:
                    logger.debug("Geth exec failing...")
                    logger.debug(str(e))
                try:
                    nr = int(out[0].replace("\n", ""))
                    if nr == len(config['priv_ips']) - 1:
                        boo = False
                        logger.info(f"Node {index} on IP {ip} is fully connected")
                        status_flags[index] = True
                    else:
                        logger.info(f"Node {index} on IP {ip} is not yet fully connected (expected: {len(config['priv_ips']) - 1}, actual: {nr} ")
                except Exception as e:
                    logger.debug(f"Node {index} might not have started at all - retrying though")
                    logger.debug(str(Exception))

    if (False in status_flags):
        try:
            logger.error(f"Failed Quorum nodes: {[config['priv_ips'][x] for x in np.where(status_flags != True)]}")
        except:
            pass
        logger.error('Quorum network start was not successful')

    return status_flags


def kill_node(config, ssh_clients, node, logger):

    logger.debug(f" --> Shutting down and resetting node {node}")
    try:
        stdin, stdout, stderr = ssh_clients[node].exec_command("pidof geth")
        pid = stdout.readlines()[0].replace("\n", "")
        # logger.debug(f"geth pid: {pid}")
        stdin, stdout, stderr = ssh_clients[node].exec_command(f"kill {pid}")
        stdout.readlines()
    except:
        logger.info(f"It seems that geth on node {node} is already killed")
        logger.info(f"Checking this")
        stdin, stdout, stderr = ssh_clients[node].exec_command("ps aux | grep geth")
        logger.info(f"stdout for ps aux | grep geth: {stdout.readlines()}")
        logger.info(f"stderr for ps aux | grep geth: {stderr.readlines()}")

    # logger.debug(f" --> Clearing the tx-pool")
    stdin, stdout, stderr = ssh_clients[node].exec_command("rm /home/ubuntu/nodes/new-node-1/geth/transactions.rlp")
    stdout.readlines()


def restart_node(config, ssh_clients, node, logger):

    kill_node(config, ssh_clients, node, logger)
    start_node(config, ssh_clients, node, logger)
    time.sleep(10)
    unlock_node(config, ssh_clients, node, logger)


def kill_network(config, ssh_clients, logger):

    logger.info("Killing geth on all nodes")
    for node, _ in enumerate(config['priv_ips']):

        kill_node(config, ssh_clients, node, logger)


def quorum_restart(config, ssh_clients, logger):

    kill_network(config, ssh_clients, logger)
    start_network(config, ssh_clients, logger)


"""


def log_outs(stdout, stderr, logger):
    out0 = stdout.readlines()
    out1 = stderr.readlines()
    try:
        logger.debug(f"{out1[1]}")
    except:
        pass


"""