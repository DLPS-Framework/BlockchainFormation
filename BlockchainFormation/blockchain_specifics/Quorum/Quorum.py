import os
import sys
import json
import time
from web3 import Web3
import numpy as np
from BlockchainFormation.utils.utils import *


def quorum_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the quorum specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['priv_ips']):
        # get account from all instances
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

    logger.info("Create directories for saving data and logs locally")
    # path = os.getcwd()
    os.mkdir((f"{config['exp_dir']}/quorum_logs"))
    os.mkdir((f"{config['exp_dir']}/tessera_logs"))

    # for saving the enodes and addresses of the nodes resp. wallets (each node has one wallet at the moment)
    addresses = []
    enodes = []

    # logger.info("rebooting all VMs...")
    # ssh_clients, scp_clients = reboot()

    logger.info("Get the addresses of each node's wallet (which have been generated during bootstrapping) and store it in the corresponding array <addresses>")
    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("cat /home/ubuntu/nodes/address")
        out = stdout.readlines()
        addresses.append(out[0].replace("\n", ""))
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))

    logger.info("Replace the genesis_raw.json on each node by genesis_raw where the first two nodes have some ether")
    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("(sed -i -e 's/substitute_first_address/'" + f"'{addresses[0]}'" + "'/g' /home/ubuntu/genesis_raw.json && sed -i -e 's/substitute_second_address/'" + f"'{addresses[1]}'" + "'/g' /home/ubuntu/genesis_raw.json && mv /home/ubuntu/genesis_raw.json /home/ubuntu/nodes/genesis.json)")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

    config['addresses'] = addresses

    logger.info("Generate the enode on each node and store it in enodes")
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

    logger.info("Generate static-nodes on each node and initialize the genesis block afterwards")
    for index1, _ in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index1].exec_command("echo '[' > /home/ubuntu/nodes/new-node-1/static-nodes.json")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

        for index2, ip2 in enumerate(config['priv_ips'][0:index1 + 1]):
            # for index2, _ in enumerate(config['priv_ips']):
            if (index2 < index1):
                # if index2 < len(config['priv_ips'])-1:
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

        # finish static-nodes.json and initialize genesis block
        stdin, stdout, stderr = ssh_clients[index1].exec_command("(echo ']' >> /home/ubuntu/nodes/new-node-1/static-nodes.json && geth --datadir /home/ubuntu/nodes/new-node-1 init /home/ubuntu/nodes/genesis.json)")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

    # starting tessera_nodes
    tessera_public_keys, tessera_private_keys = start_tessera_nodes(config, ssh_clients, logger)
    config['tessera_public_keys'] = tessera_public_keys
    config['tessera_private_keys'] = tessera_private_keys

    # starting quorum nodes
    start_quorum_nodes(config, ssh_clients, scp_clients, logger)


def start_tessera_nodes(config, ssh_clients, logger):
    # for saving the public and private keys of the tessera nodes (enclaves)
    tessera_public_keys = []
    tessera_private_keys = []

    logger.info("Get tessera-data from each node and create config-file for tessera on each node")
    for index1, ip1 in enumerate(config['priv_ips']):

        # get tessera public and private keys (which have been generated during bootstrapping) and store them in the corresponding arrays <tessera_public_keys> resp. <tessera_private_keys>
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

        # build peer string which is then inserted to config_raw.json, which contains all tessera-specific information,
        # in particular the peers / tessera-nodes which will participate in the (private) quorum network
        peer_string = '\\"peer\\":\ ['

        for index2, ip2 in enumerate(config['priv_ips']):

            if index2 < len(config['priv_ips']) - 1:
                peer_string = peer_string + '{\\"url\\":\ \\"http://' + f'{ip2}' + ':9000\\"},'
            else:
                peer_string = peer_string + '{\\"url\\":\ \\"http://' + f'{ip2}' + ':9000\\"}'

        peer_string = peer_string + "],"

        # Specify missing data in config_raw.json and store the result in config.json
        stdin, stdout, stderr = ssh_clients[index1].exec_command(f"(sed -i -e s#substitute_ip#{ip1}#g /home/ubuntu/config_raw.json && sed -i -e s#substitute_public_key#{tessera_public_keys[index1]}#g /home/ubuntu/config_raw.json && sed -i -e s#substitute_private_key#{tessera_private_keys[index1]}#g /home/ubuntu/config_raw.json && sed -i -e s#substitute_peers#" + peer_string + "#g /home/ubuntu/config_raw.json && mv /home/ubuntu/config_raw.json /home/ubuntu/qdata/tm/config.json)")
        stdout.readlines()

        logger.info(f"Starting tessera on node {index1}")
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("java -jar tessera/tessera-app-0.9.2-app.jar -configfile qdata/tm/config.json >> tessera.log 2>&1")

    logger.info("Waiting until all tessera nodes have started")
    boo = wait_till_done(config, ssh_clients, config['ips'], 60, 10, '/home/ubuntu/qdata/tm/tm.ipc', False, 10, logger)
    """
    status_flags = np.zeros(config['vm_count'], dtype=bool)
    timer = 0
    while (False in status_flags and timer < 10):
        time.sleep(10)
        timer += 1
        logger.info(f" --> Waited {timer*10} seconds so far, {100 - timer*10} seconds left before abort (it usually takes around 10 seconds)")
        for index, ip in enumerate(config['priv_ips']):

            if (status_flags[index] == False):
                sftp = ssh_clients[index].open_sftp()
                try:
                    sftp.stat('/home/ubuntu/qdata/tm/tm.ipc')
                    status_flags[index] = True
                    logger.info(f"   --> Tessera node on {ip} is ready")
                except IOError:
                    logger.info(f"   --> Tessera node on {ip} is not ready yet")

    if (False in status_flags):
        logger.error('Boot up NOT successful')
        exit -1
        try:
            logger.error(f"Failed Tessera nodes: {[config['priv_ips'][x] for x in np.where(status_flags != True)]}")
        except:
            pass

    """
    if boo == False:
        raise Exception("At least one tessera node did not start properly")

    return tessera_public_keys, tessera_private_keys


def start_quorum_nodes(config, ssh_clients, scp_clients, logger):
    logger.info("Starting the quorum network...")

    string_geth_settings = ""
    for key in config['quorum_settings']:
        if key != "private_fors":
            value = config['quorum_settings'][f"{key}"]
            string_geth_settings = string_geth_settings + f" --{key} {value}"

    logger.debug(f"settings:{string_geth_settings}")

    for index, ip in enumerate(config['priv_ips']):

        if index == 0:
            logger.info(f" --> Starting node {index} and wait for 5s until it is running")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"PRIVATE_CONFIG=/home/ubuntu/qdata/tm/tm.ipc geth --datadir /home/ubuntu/nodes/new-node-1 --nodiscover --verbosity 5 --networkid 31337 --raft --maxpeers {config['vm_count']} --raftport 50000 --rpc --rpcaddr 0.0.0.0 --rpcport 22000 --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft --emitcheckpoints --port 21000 --nat=extip:{ip}{string_geth_settings} >>node.log 2>&1")
            time.sleep(5)

        else:
            logger.info(f" --> Adding node {index} to raft on node {0} and starting it afterwards")
            stdin, stdout, stderr = ssh_clients[0].exec_command("geth --exec " + '\"' + "raft.addPeer('enode://" + f"{config['enodes'][index]}" + "@" + f"{ip}" + ":21000?discport=0&raftport=50000')" + '\"' + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
            out = stdout.readlines()
            # logger.debug(out)
            # logger.debug("".join(stderr.readlines()))
            raftID = out[0].replace("\x1b[0m\r\n", "").replace("\x1b[31m", "").replace("\n", "")
            # logger.info(f"raftID: {raftID}")

            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"PRIVATE_CONFIG=/home/ubuntu/qdata/tm/tm.ipc geth --datadir /home/ubuntu/nodes/new-node-1 --nodiscover --verbosity 5 --networkid 31337 --raft --maxpeers {config['vm_count']} --raftport 50000 --raftjoinexisting {raftID} --rpc --rpcaddr 0.0.0.0 --rpcport 22000 --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft --emitcheckpoints --port 21000 --nat=extip:{ip}{string_geth_settings} >>node.log 2>&1")

    boo = wait_till_done(config, ssh_clients, config['ips'], 60, 10, '/home/ubuntu/nodes/new-node-1/geth.ipc', False, 10, logger)
    if boo == False:
        raise Exception("At least one quorum node did not start properly")

    logger.info("Testing whether the system has started successfully")
    status_flags = np.zeros(config['vm_count'], dtype=bool)
    timer = 0
    while (False in status_flags and timer < 12):
        time.sleep(10)
        timer += 1
        logger.info(
            f" --> Waited {timer * 10} seconds so far, {120 - timer * 10} seconds left before abort (it usually takes around 10 seconds)")
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
        raise Exception("Blockchain did not start properly - Omitting or repeating")


    logger.info("")
    logger.info("================================")
    logger.info("Quorum network is running now...")
    logger.info("================================")
    logger.info("")

    logger.info("Unlocking all accounts forever")
    boo = True
    for index, ip in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command("geth --exec eth.accounts attach /home/ubuntu/nodes/new-node-1/geth.ipc")
        out = stdout.readlines()
        sender = out[0].replace("\n", "").replace("[", "").replace("]", "")

        stdin, stdout, stderr = ssh_clients[index].exec_command("geth --exec " + "\'" + f"personal.unlockAccount({sender}, " + '\"' + "user" + '\"' + ", 0)" + "\'" + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
        out = stdout.readlines()
        if out[0].replace("\n", "") != "true":
            boo = False
            logger.info(f"Something went wrong on unlocking on node {index} on IP {ip}")

    if boo == True:
        logger.info("All accounts unlocked")
        logger.info("")

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


"""

methods in development - necessary for more compact stdout logging resp. node killing and reviving in case the network breaks down
not prioritized since full setup is okay, does not take too long and time is sparse

def kill_node(ssh_clients, index, logger):
    # stdin, stdout, stderr = ssh_clients[index].exec_command("pidof java")
    # pid = stdout.readlines()[0].replace("\n", "")
    # stdin, stdout, stderr = ssh_clients.exec_command(f"kill {pid}")
    # logger.debug(f"tessera pid: {pid}")
    stdin, stdout, stderr = ssh_clients[index].exec_command("pidof geth")
    pid = stdout.readlines()[0].replace("\n", "")
    logger.debug(f"geth pid: {pid}")
    stdin, stdout, stderr = ssh_clients[index].exec_comand(f"kill {pid}")

def revive_node(config, ssh_clients, index, logger):
    pass

def log_outs(stdout, stderr, logger):
    out0 = stdout.readlines()
    out1 = stderr.readlines()
    try:
        logger.debug(f"{out1[1]}")
    except:
        pass

"""