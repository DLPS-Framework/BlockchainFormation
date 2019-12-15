#  Copyright 2019 BMW Group
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
import random

def sawtooth_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the sawtooth specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['ips']):
        # get account from all instances
        scp_clients[index].get("/var/log/sawtooth", f"{config['exp_dir']}/sawtooth_logs/sawtooth_logs_node_{index}", recursive=True)
        scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


def sawtooth_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """

    # the indices of the blockchain nodes
    config['node_indices'] = list(range(0, config['vm_count']))

    dir_name = os.path.dirname(os.path.realpath(__file__))

    logger.info("Creating directories for saving data and logs locally")
    os.mkdir(f"{config['exp_dir']}/sawtooth_logs")

    logger.info("Changing permissions of log directory such that logs can be pulled via scp later")
    for index, _ in enumerate(config['priv_ips']):
        os.mkdir(f"{config['exp_dir']}/sawtooth_logs/sawtooth_logs_node_{index}")
        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo chown -R sawtooth:ubuntu /var/log/sawtooth")
        stdout.readlines()

    logger.debug("Checking whether installation on first node was successfull")
    stdin, stdout, stderr = ssh_clients[0].exec_command("dpkg -l '*sawtooth*'")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    logger.info("Adapting config (.toml)-file for validator, starting sawtooth-services and finalizing setup on all nodes")
    for index1, ip1 in enumerate(config['priv_ips']):

        # Creating string for binding specification and replace substitute_binding
        binding_string = f'\\"network:tcp://{ip1}:8800\\",'
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_bind#" + binding_string + "#g /data/validator.toml")
        stdout.readlines()

        # Creating string for endpoint speficifation and replace substitute_endpoint
        endpoint_string = f'endpoint\ =\ \\"tcp://{ip1}:8800\\"'
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_endpoint#" + endpoint_string + "#g /data/validator.toml")
        stdout.readlines()

        if len(config['priv_ips']) == 1:
            peer_string = "# no peers"
        else:
            # create string for peers
            logger.debug(f"finalizing setup on node {index1}")
            peer_string = "peers\ =\ ["
            for index2, ip2 in enumerate(config['priv_ips']):
                if index2 != index1:
                    if peer_string != "peers\ =\ [":
                        peer_string = peer_string + ",\ "
                    peer_string = peer_string + f'\\"tcp://{ip2}:8800\\"'

            peer_string = peer_string + "]"

        if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":
            peer_string = ""

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_peers#" + peer_string + "#g /data/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        logger.debug("Adjusting minimum and maximum peer connectivity")
        min_connectivity_string = f"{len(config['priv_ips']) - 1}"
        max_connectivity_string = f"{2 * (len(config['priv_ips']) - 1)}"
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_min_connectivity#" + min_connectivity_string + "#g /data/validator.toml")
        stdout.readlines()

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_max_connectivity#" + max_connectivity_string + "#g /data/validator.toml")
        stdout.readlines()

        logger.debug("adjusting REST-API config")
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_local_private_ip#" + ip1 + "#g /data/rest_api.toml")
        stdout.readlines()

        logger.debug("Replacing the configs in /etc/sawtooth by the customized configs")
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /data/validator.toml /etc/sawtooth/validator.toml")
        stdout.readlines()

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /data/rest_api.toml /etc/sawtooth/rest_api.toml")
        stdout.readlines()

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /data/cli.toml /etc/sawtooth/cli.toml")
        stdout.readlines()

    sawtooth_start(config, ssh_clients, scp_clients, logger)


def sawtooth_start(config, ssh_clients, scp_clients, logger):

    user = ""
    key_path = "/home/ubuntu/.sawtooth/keys/ubuntu.priv"
    tmp_path = "/home/ubuntu/temp"

    logger.debug(("Creating a temporary directory"))
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}mkdir {tmp_path}")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    logger.debug("Creating config-genesis.batch")
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset genesis --key {key_path} -o {tmp_path}/config-genesis.batch")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "DEVMODE":

        logger.debug("Creating config-consensus.batch for Devmode")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.consensus.algorithm.name=Devmode sawtooth.consensus.algorithm.version=0.1 -o {tmp_path}/config-consensus.batch")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        logger.debug("Creating genesis block for Devmode")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis {tmp_path}/config-genesis.batch {tmp_path}/config-consensus.batch")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        logger.debug("Starting all services for Devmode")
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS validator sudo -u sawtooth sawtooth-validator -vv")
        time.sleep(5)
        channel = ssh_clients[0].get_transport().open_session()
        # channel.exec_command(f"sudo -u sawtooth sawtooth-rest-api -v --bind {config['priv_ips'][0]}:8008")
        channel.exec_command(f"screen -dmS rest sudo -u sawtooth sawtooth-rest-api -vv --bind {config['priv_ips'][0]}:8008")
        time.sleep(1)
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS settings sudo -u sawtooth settings-tp -vv")
        time.sleep(1)
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS intkey sudo -u sawtooth intkey-tp-python -vv")
        time.sleep(5)
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS engine sudo -u sawtooth devmode-engine-rust -vv --connect tcp://localhost:5050")

    else:

        logger.debug("Get all the public keys")
        validator_pub_keys = []
        string_raft_peers = '['
        string_pbft_peers = '['
        for index in range(0, len(config['priv_ips'])):
            stdin, stdout, stderr = ssh_clients[index].exec_command("cat /etc/sawtooth/keys/validator.pub")
            key = stdout.readlines()[0].replace("\n", "")

            validator_pub_keys.append(key)
            if index == 0:
                string_pbft_peers = string_pbft_peers + f'\"{key}\"'
                string_raft_peers = string_raft_peers + f'\"{key}\"'

            else:
                string_pbft_peers = string_pbft_peers + f',\"{key}\"'
                string_raft_peers = string_raft_peers + f',\"{key}\"'

        string_pbft_peers = string_pbft_peers + f']'
        string_raft_peers = string_raft_peers + f']'

        logger.debug(f"List of public keys for raft: {string_raft_peers}")
        logger.debug(f"List of public keys fo pbft: {string_pbft_peers}")

        logger.info("Doing special config stuff for first node")
        logger.debug("Creating genesis config on first node")

        if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "POET":

            logger.debug("Creating config-consensus.batch for PoET")
            stdin, stdout, stderr = ssh_clients[0].exec_command(
                f'{user}sawset proposal create --key {key_path} sawtooth.consensus.algorithm.name=PoET sawtooth.consensus.algorithm.version=0.1 sawtooth.poet.report_public_key_pem="$(cat /etc/sawtooth/simulator_rk_pub.pem)" sawtooth.poet.valid_enclave_measurements=$(poet enclave measurement) sawtooth.poet.valid_enclave_basenames=$(poet enclave basename) -o {tmp_path}/config-consensus.batch')
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            logger.debug("Creating poet.batch")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo poet registration create --key /etc/sawtooth/keys/validator.priv -o {tmp_path}/poet.batch")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            # logger.debug("Creating poet-settings.batch")
            # stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.poet.target_wait_time=5 sawtooth.poet.initial_wait_time=25 sawtooth.publisher.max_batches_per_block=100 -o {tmp_path}/poet-settings.batch")
            # logger.debug(stdout.readlines())
            # logger.debug(stderr.readlines())

            logger.debug("Creating genesis block for PoET using the just created config.batches")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis {tmp_path}/config-genesis.batch {tmp_path}/config-consensus.batch {tmp_path}/poet.batch")
            logger.debug("".join(stdout.readlines()))
            logger.debug("".join(stderr.readlines()))

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "PBFT":

            logger.debug("Creating config-consensus.batch")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.consensus.algorithm.name=pbft sawtooth.consensus.algorithm.version=1.0 sawtooth.consensus.pbft.members='{string_pbft_peers}' -o {tmp_path}/config-consensus.batch")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            # logger.debug("Creating bbft-settings.batch")
            # stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.consensus.pbft.block_publishing_delay=2000 -o {tmp_path}/pbft-settings.batch")
            # logger.debug(stdout.readlines())
            # logger.debug(stderr.readlines())

            logger.debug("Creating genesis block for PBFT using the just created config.batches")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis {tmp_path}/config-genesis.batch {tmp_path}/config-consensus.batch")
            logger.debug("".join(stdout.readlines()))
            logger.debug("".join(stderr.readlines()))

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":

            logger.debug("Creating config-consensus.batch")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.consensus.algorithm.name=raft sawtooth.consensus.algorithm.version=0.1 sawtooth.consensus.raft.peers='{string_raft_peers}' -o {tmp_path}/config-consensus.batch")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            # logger.debug("Creating bbft-settings.batch")
            # stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.consensus.pbft.block_publishing_delay=2000 -o {tmp_path}/pbft-settings.batch")
            # logger.debug(stdout.readlines())
            # logger.debug(stderr.readlines())

            logger.debug("Creating genesis block for RAFT using the just created config.batches")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis {tmp_path}/config-genesis.batch {tmp_path}/config-consensus.batch")
            logger.debug("".join(stdout.readlines()))
            logger.debug("".join(stderr.readlines()))

        """
        stdin, stdout, stderr = ssh_clients[0].exec_command("mkdir /data/sawtooth")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo ls -la /var/lib/sawtooth | awk '{print $9}' | grep -e genesis -e poet")
        genesis_files = stdout.readlines()
        logger.debug(genesis_files)
        logger.debug(stderr.readlines())

        for file in genesis_files:
            logger.debug(f"filename: {file}")
            file = file.reaplace("\n", "")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo cp /var/lib/sawtooth/{file} /data/sawtooth/{file}")
            logger.debug("".join(stdout.readlines()))
            logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo cp -r /var/lib/sawtooth /data")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        """

    for index1, ip1 in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo chown -R sawtooth:sawtooth /var/lib/sawtooth")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        logger.debug("Starting all services")


        peer_string = ""

        if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":
            for index2 in range(0, index1):
                if peer_string == "":
                    peer_string = " --peering static --peers "
                else:
                    peer_string = peer_string + ","
                peer_string = peer_string + f"tcp://{config['priv_ips'][index2]}:8800"

        logger.debug(f"Starting validator with screen -dmS validator sudo -u sawtooth sawtooth-validator -vv{peer_string}")
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command(f"screen -dmS validator sudo -u sawtooth sawtooth-validator -vv{peer_string}")
        time.sleep(5)

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -dmS rest sudo -u sawtooth sawtooth-rest-api -vv")
        time.sleep(1)

        if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "POET":

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("screen -dmS registry sudo -u sawtooth poet-validator-registry-tp -vv")
            time.sleep(1)

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("screen -dmS engine sudo -u sawtooth poet-engine -vv")
            time.sleep(1)

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "PBFT":

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("screen -dmS engine sudo -u sawtooth pbft-engine -vv")
            time.sleep(1)

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":

            logger.debug(f"Starting RAFT engine with screen -dmS engine sudo -u sawtooth raft-engine --connect tcp://localhost:5050 -vvv")

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command(f"screen -dmS engine sudo -u sawtooth raft-engine --connect tcp://localhost:5050 -vvv")
            time.sleep(1)

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -dmS settings sudo -u sawtooth settings-tp -vv")
        time.sleep(1)

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -dmS intkey sudo -u sawtooth intkey-tp-python -vv")
        time.sleep(1)

    logger.info("Waiting for 10s until all nodes have started")

    # TODO wait until all peers are in list instead of hard-coded network
    time.sleep(10)
    logger.info("All nodes have started")

    start_processors(config, ssh_clients, scp_clients, logger)
    check_network(config, ssh_clients, scp_clients, logger)


def sawtooth_stop(config, ssh_clients, scp_clients, logger):


    for index1, ip1 in enumerate(config['priv_ips']):

        """
 
        logger.debug("Stopping all services...")
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-rest-api.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-validator.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-settings-tp.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-identity-tp.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-intkey-tp-python.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-poet-validator-registry-tp.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl stop sawtooth-poet-engine.service")

        logger.debug("Stopping the BenchContract processor...")
        stdin, stdout, stderr = ssh_clients[index1].exec_command("ps aux | grep -e python3 -e sawtooth")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())
        # stdin, stdout, stderr = ssh_clients[index1].exec_command("ps aux | grep -e python3 -e sawtooth | awk '{print $2}'")
        stdin, stdout, stderr = ssh_clients[index1].exec_command("ps aux | grep 'python3 /processor/main.py' | awk '{print $2}'")
        out = stdout.readlines()
        logger.debug(f"processes: {out}")
        for pid in out:
            pid = pid.replace("\n", "")
            stdin, stdout, stderr = ssh_clients[index1].exec_command(f"sudo kill {pid}")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

        """

        stdin, stdout, stderr = ssh_clients[index1].exec_command("screen -list")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        logger.info("Killing all sawtooth services and the benchcontract processor")

        stdin, stdout, stderr = ssh_clients[index1].exec_command("screen -list | grep Detached | cut -d. -f1 | awk '{print $1}' | xargs kill")
        logger.debug(stdout.readlines())
        logger.debug(stdout.readlines())

        stdin, stdout, stderr = ssh_clients[index1].exec_command("screen -list")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        time.sleep(5)

        logger.debug("Deleting ledger data")

        if index1 == 0:
            stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo rm -r /home/ubuntu/temp")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo rm -r /var/lib/sawtooth && sudo mkdir /var/lib/sawtooth && sudo chown -R sawtooth: /var/lib/sawtooth")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo rm -r /var/log/sawtooth && sudo mkdir /var/log/sawtooth && sudo chown -R sawtooth: /var/log/sawtooth")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())


def sawtooth_restart(config, ssh_clients, scp_clients, logger):

    sawtooth_stop(config, ssh_clients, scp_clients, logger)
    sawtooth_start(config, ssh_clients, scp_clients, logger)


def start_processors(config, ssh_clients, scp_clients, logger):

    for node, _ in enumerate(config['priv_ips']):
        time.sleep(5)
        dir_name = os.path.dirname(os.path.realpath(__file__))
        logger.debug("Starting BenchContract...")
        scp_clients[node].put(dir_name + "/processor", "/data", recursive=True)
        channel = ssh_clients[node].get_transport().open_session()
        channel.exec_command("screen -dmS benchcontract python3 /data/processor/main.py")


def check_network(config, ssh_clients, scp_clients, logger):

    user = ""
    key_path = "/home/ubuntu/.sawtooth/keys/ubuntu.priv"
    tmp_path = "/home/ubuntu/temp"

    boo1 = True

    if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "DEVMODE":
        pass
    else:
        logger.info("Checking whether setup has been successful by searching for every peer in sawtooth peer list")
        for index, ip in enumerate(config['ips']):

            stdin, stdout, stderr = ssh_clients[index].exec_command(f"sawtooth peer list --url http://{config['priv_ips'][index]}:8008")
            out = stdout.readlines()
            try:
                peer_list = set(out[0].replace("\n", "").split(","))
                if len(peer_list) != len(config['priv_ips'])-1:
                    boo1 = False
                    logger.info(f"Node {index} on IP {ip} has not connected properly")

            except:
                logger.info(f"Something went wrong - sawtooth peer list not working")
                boo1 = False

    if boo1 is True or config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "DEVMODE":
            logger.info(f"All nodes seem to have connected properly")

    logger.info("Adapting the sawtooth specific properties such as consensus algorithm, block time, ...")
    for key in config["sawtooth_settings"]:
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo sawset proposal create --url http://{config['priv_ips'][0]}:8008 --key {key_path} {key}={config['sawtooth_settings'][key]}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    logger.info("Checking whether these proposals have been adopted")
    time.sleep(10)
    stdin, stdout, stderr = ssh_clients[-1].exec_command(f"sawtooth settings list --url http://{config['priv_ips'][-1]}:8008")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))


    logger.info("Checking whether intkey is working on every peer by making one set operation and reading on all nodes")


    value = random.randint(0, 10000)
    key = f"val{value}"


    ssh_clients[len(config['priv_ips'])-1].exec_command(f"intkey set {key} {value} --url http://{config['priv_ips'][0]}:8008")
    time.sleep(5)
    boo2 = True
    for index, ip in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"intkey show {key} --url http://{config['priv_ips'][index]}:8008")
        out = stdout.readlines()
        try:
            if (out[0].replace("\n", "") != f"{key}: {value}"):
                boo2 = False
                logger.info(f"Node {index} on IP {ip} not working properly")
            else:
                logger.info(f"Node {index} in IP {ip} is working properly")

        except:
            logger.info("Something went wrong - sawtooth intkey is not working")
            boo2 = False

    if boo2 == True:
        logger.info("Intkey working properly on all nodes")

    if boo1 == True and boo2 == True:
        logger.info("Sawtooth network setup was successful")
    else:
        logger.info("Sawtooth network setup was NOT successful")
        raise Exception("Blockchain did not start properly - Omitting or repeating")
