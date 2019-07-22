import os
import sys
import json
import time
from web3 import Web3
import numpy as np

def quorum_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the quorum specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['pub_ips']):
        # get account from all instances
        scp_clients[index].get("/home/ubuntu/node.log", f"{config['exp_dir']}/quorum_logs/quorum_log_node_{index}.log")
        scp_clients[index].get("/home/ubuntu/tessera.log", f"{config['exp_dir']}/tessera_logs/tessera_log_node_{index}.log")
        scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


def quorum_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """
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
    for index, _ in enumerate(config['pub_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command("cat /home/ubuntu/nodes/address")
        out = stdout.readlines()
        addresses.append(out[0].replace("\n", ""))
        logger.debug(out)
        logger.debug("".join(stderr.readlines()))

    logger.info("Replace the genesis_raw.json on each node by genesis_raw where the first two nodes have some ether")
    for index, _ in enumerate(config['pub_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command("sed -i -e 's/substitute_first_address/'" + f"'{addresses[0]}'" + "'/g' /home/ubuntu/genesis_raw.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index].exec_command("sed -i -e 's/substitute_second_address/'" + f"'{addresses[1]}'" + "'/g' /home/ubuntu/genesis_raw.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index].exec_command("mv /home/ubuntu/genesis_raw.json /home/ubuntu/nodes/genesis.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

    config['addresses'] = addresses

    logger.info("Generate the enode on each node and store it in enodes")
    for index, _ in enumerate(config['pub_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command("bootnode --genkey=nodekey")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index].exec_command("mv nodekey /home/ubuntu/nodes/new-node-1/nodekey")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index].exec_command("bootnode --nodekey=/home/ubuntu/nodes/new-node-1/nodekey --writeaddress")
        out = stdout.readlines()
        enodes.append(out[0].replace("\n", "").replace("]", "").replace("[", ""))
        logger.debug(out)
        logger.debug("".join(stderr.readlines()))

    config['enodes'] = enodes

    logger.info("Generate static-nodes on each node and initialize the genesis block afterwards")
    for index1, _ in enumerate(config['pub_ips']):

        stdin, stdout, stderr = ssh_clients[index1].exec_command("echo '[' > /home/ubuntu/nodes/new-node-1/static-nodes.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        for index2, ip2 in enumerate(config['pub_ips'][0:index1 + 1]):
            # for index2, _ in enumerate(config['pub_ips']):
            if (index2 < index1):
                # if index2 < len(config['pub_ips'])-1:
                string = "echo '  " + '\"' + "enode://" + f"{enodes[index2]}" + "@" + f"{ip2}" + ":21000?discport=0&raftport=50000'" + '\\",' + " >> /home/ubuntu/nodes/new-node-1/static-nodes.json"
                stdin, stdout, stderr = ssh_clients[index1].exec_command(string)
                logger.debug("".join(stdout.readlines()))
                logger.debug("".join(stderr.readlines()))
            else:
                string = "echo '  " + '\"' + "enode://" + f"{enodes[index2]}" + "@" + f"{ip2}" + ":21000?discport=0&raftport=50000'" + '\\"' + " >> /home/ubuntu/nodes/new-node-1/static-nodes.json"
                stdin, stdout, stderr = ssh_clients[index1].exec_command(string)
                logger.debug("".join(stdout.readlines()))
                logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("echo ']' >> /home/ubuntu/nodes/new-node-1/static-nodes.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        # initialize genesis block
        stdin, stdout, stderr = ssh_clients[index1].exec_command("geth --datadir /home/ubuntu/nodes/new-node-1 init /home/ubuntu/nodes/genesis.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

    # for saving the public and private keys of the tessera nodes (enclaves)
    tessera_public_keys = []
    tessera_private_keys = []

    logger.info("Get tessera-data from each node and create config-file for tessera on each node")
    for index1, ip1 in enumerate(config['pub_ips']):

        # get tessera public and private keys (which have been generated during bootstrapping) and store them in the corresponding arrays <tessera_public_keys> resp. <tessera_private_keys>
        stdin, stdout, stderr = ssh_clients[index1].exec_command("cat /home/ubuntu/qdata/tm/tm.pub")
        out = stdout.readlines()
        logger.debug("".join(out))
        logger.debug("".join(stderr.readlines()))
        tessera_public_keys.append(out[0].replace("\n", ""))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("cat /home/ubuntu/qdata/tm/tm.key")
        out = stdout.readlines()
        logger.debug("".join(out))
        logger.debug("".join(stderr.readlines()))
        tessera_private_keys.append(out[3].replace('      "bytes" : ', "").replace('\n', ""))

        # build peer string which is then inserted to config_raw.json, which contains all tessera-specific information,
        # in particular the peers / tessera-nodes which will participate in the (private) quorum network
        peer_string = '\\"peer\\":\ ['

        for index2, ip2 in enumerate(config['pub_ips']):

            if index2 < len(config['pub_ips']) - 1:
                peer_string = peer_string + '{\\"url\\":\ \\"http://' + f'{ip2}' + ':9000\\"},'
            else:
                peer_string = peer_string + '{\\"url\\":\ \\"http://' + f'{ip2}' + ':9000\\"}'

        peer_string = peer_string + "],"

        # Specify missing data in config_raw.json and store the result in config.json
        stdin, stdout, stderr = ssh_clients[index1].exec_command(f"sed -i -e s#substitute_ip#{ip1}#g /home/ubuntu/config_raw.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command(f"sed -i -e s#substitute_public_key#{tessera_public_keys[index1]}#g /home/ubuntu/config_raw.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command(f"sed -i -e s#substitute_private_key#{tessera_private_keys[index1]}#g /home/ubuntu/config_raw.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command(f"sed -i -e s#substitute_peers#" + peer_string + "#g /home/ubuntu/config_raw.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("mv /home/ubuntu/config_raw.json /home/ubuntu/qdata/tm/config.json")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        logger.info(f"Starting tessera on node {index1}")
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("java -jar tessera/tessera-app-0.9.2-app.jar -configfile qdata/tm/config.json >> tessera.log 2>&1")

    logger.info("Waiting until all tessera nodes have started")
    status_flags = np.zeros(config['vm_count'], dtype=bool)
    timer = 0
    while (False in status_flags and timer < 10):
        time.sleep(10)
        timer += 1
        logger.info(f" --> Waited {timer*10} seconds so far, {100 - timer*10} seconds left before abort (it usually takes around 10 seconds)")
        for index, ip in enumerate(config['pub_ips']):

            if (status_flags[index] == False):
                sftp = ssh_clients[index].open_sftp()
                try:
                    sftp.stat('/home/ubuntu/qdata/tm/tm.ipc')
                    status_flags[index] = True
                    logger.info(f"Tessera node on {ip} is ready")
                except IOError:
                    logger.info(f"Tessera node on {ip} not ready")

    if (False in status_flags):
        logger.error('Boot up NOT successful')
        exit -1
        try:
            logger.error(f"Failed Tessera nodes: {[config['pub_ips'][x] for x in np.where(status_flags != True)]}")
        except:
            pass

    config['tessera_public_keys'] = tessera_public_keys
    config['tessera_private_keys'] = tessera_private_keys

    logger.info("Starting the quorum network...")
    for index, ip in enumerate(config['pub_ips']):

        if index == 0:
            logger.info(f"Starting node {index} and wait for 5s until it is running")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"PRIVATE_CONFIG=/home/ubuntu/qdata/tm/tm.ipc geth --datadir /home/ubuntu/nodes/new-node-1 --nodiscover --verbosity 5 --networkid 31337 --raft --raftport 50000 --rpc --rpcaddr 0.0.0.0 --rpcport 22000 --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft --emitcheckpoints --port 21000 --nat=extip:{ip} --raftblocktime {config['quorum_settings']['raftblocktime']} >>node.log 2>&1")
            time.sleep(5)

        else:
            logger.info(f"Adding node {index} to raft on node {0} and starting it afterwards")
            stdin, stdout, stderr = ssh_clients[0].exec_command("geth --exec " + '\"' + "raft.addPeer('enode://" + f"{enodes[index]}" + "@" + f"{ip}" + ":21000?discport=0&raftport=50000')" + '\"' + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
            out = stdout.readlines()
            logger.debug(out)
            logger.debug("".join(stderr.readlines()))
            raftID = out[0].replace("\x1b[0m\r\n", "").replace("\x1b[31m", "").replace("\n", "")
            logger.info(f"raftID: {raftID}")

            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"PRIVATE_CONFIG=/home/ubuntu/qdata/tm/tm.ipc geth --datadir /home/ubuntu/nodes/new-node-1 --nodiscover --verbosity 5 --networkid 31337 --raft --raftport 50000 --raftjoinexisting {raftID} --rpc --rpcaddr 0.0.0.0 --rpcport 22000 --rpcapi admin,db,eth,debug,miner,net,shh,txpool,personal,web3,quorum,raft --emitcheckpoints --port 21000 --nat=extip:{ip} --raftblocktime {config['quorum_settings']['raftblocktime']} >>node.log 2>&1")


    logger.info("Waiting until all quorum nodes have started")
    status_flags = np.zeros(config['vm_count'], dtype=bool)
    timer = 0
    while (False in status_flags and timer < 10):
        time.sleep(10)
        timer += 1
        logger.info(f" --> Waited {timer*10} seconds so far, {100 - timer*10} seconds left before abort (it usually takes around 10 seconds)")
        for index, ip in enumerate(config['pub_ips']):

            if (status_flags[index] == False):
                sftp = ssh_clients[index].open_sftp()
                try:
                    sftp.stat('/home/ubuntu/nodes/new-node-1/geth.ipc')
                    status_flags[index] = True
                    logger.info(f"Quorum node on {ip} is ready")
                except IOError:
                    logger.info(f"Quorum node on {ip} not ready")

    if (False in status_flags):
        logger.error('Boot up NOT successful')
        exit -1
        try:
            logger.error(f"Failed Quorum nodes: {[config['pub_ips'][x] for x in np.where(status_flags != True)]}")
        except:
            pass


    logger.info("Testing whether the system has started successfully")
    boo = True
    for index, ip in enumerate(config['pub_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command("geth --exec " + '\"' + "admin.peers.length" + '\"' + " attach /home/ubuntu/nodes/new-node-1/geth.ipc")
        out = stdout.readlines()
        if int(out[0].replace("\n", "")) != len(config['priv_ips'])-1:
            boo = False
            logger.info(f"Node {index} on IP {ip} not fully connected")

    if boo == True:
        logger.info("Quorum network is running now...")
        logger.info("")

    logger.info("Unlocking all accounts forever")
    boo = True
    for index, ip in enumerate(config['pub_ips']):

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

    logger.info("Getting logs from vms")

    for index, ip in enumerate(config['pub_ips']):
        scp_clients[index].get("/var/log/user_data.log",
                               f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


    try:
        scp_clients[index].get("/home/ubuntu/tessera.log", f"{config['exp_dir']}/tessera_logs/tessera_node{index}.log")
        logger.info("Logs fetched successfully")
    except:
        logger.info(f"Not all tessera logs available on {ip}")



    try:
        scp_clients[index].get("/home/ubuntu/node.log", f"{config['exp_dir']}/quorum_logs/quorum_node{index}.log")
        logger.info("Logs fetched successfully")
    except:
        logger.info(f"Not all quorum logs available on {ip}")

    logger.info("")

