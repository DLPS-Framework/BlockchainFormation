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
import random

from BlockchainFormation.utils.utils import *


def sawtooth_check_config(config, logger):

    logger.debug(f"Checking the sawtooth config")
    if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "DEVMODE":
        if config['vm_count'] != 1:
            raise Exception("Devmode only works with one node")

    elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "POET":
        if config['vm_count'] < 3:
            raise Exception("PoET consensus only works with at least 3 nodes")

    elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "PBFT":
        if config['vm_count'] < 4:
            raise Exception("PBFT consensus only works with at least 4 nodes")
    elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":
        pass
    else:
        raise Exception("Currently, only Devmode, PoET, RAFT, and PBFT consensus are supported")


def sawtooth_shutdown(config, logger, ssh_clients, scp_clients):

    """
    runs the sawtooth specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    logger.info("Fetching the sawtooth logs")
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

    # uploading the benchcontract processor (smart contract code)
    upload_processors(config, scp_clients, logger)

    logger.info("Creating directories for saving data and logs locally")
    os.mkdir(f"{config['exp_dir']}/sawtooth_logs")

    logger.info("Changing permissions of log directory such that logs can be pulled via scp later")
    for index, _ in enumerate(config['priv_ips']):
        os.mkdir(f"{config['exp_dir']}/sawtooth_logs/sawtooth_logs_node_{index}")
        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo chown -R sawtooth:ubuntu /var/log/sawtooth")
        stdout.readlines()

    logger.debug("Checking whether installation on first node was successful")
    stdin, stdout, stderr = ssh_clients[0].exec_command("dpkg -l '*sawtooth*'")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    logger.info("Adapting config (.toml)-file for validator, REST-API, and CLI")
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
            # Creating the string for peers
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
        wait_and_log(stdout, stderr)

        # Adjusting minimum and maximum peer connectivity
        min_connectivity_string = f"{len(config['priv_ips']) - 1}"
        max_connectivity_string = f"{2 * (len(config['priv_ips']) - 1)}"
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_min_connectivity#" + min_connectivity_string + "#g /data/validator.toml")
        wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_max_connectivity#" + max_connectivity_string + "#g /data/validator.toml")
        wait_and_log(stdout, stderr)

        # Adjusting REST-API config
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_local_private_ip#" + ip1 + "#g /data/rest_api.toml")
        wait_and_log(stdout, stderr)

        # Replacing the configs in /etc/sawtooth by the customized configs
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /data/validator.toml /etc/sawtooth/validator.toml")
        wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /data/rest_api.toml /etc/sawtooth/rest_api.toml")
        wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /data/cli.toml /etc/sawtooth/cli.toml")
        wait_and_log(stdout, stderr)

    sawtooth_start(config, ssh_clients, logger)


def sawtooth_start(config, ssh_clients, logger):

    user = ""
    key_path = "/home/ubuntu/.sawtooth/keys/ubuntu.priv"
    tmp_path = "/home/ubuntu/temp"

    logger.debug("Creating a temporary directory")
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}mkdir {tmp_path}")
    wait_and_log(stdout, stderr)

    logger.debug("Creating config-genesis.batch")
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset genesis --key {key_path} -o {tmp_path}/config-genesis.batch")
    wait_and_log(stdout, stderr)

    if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "DEVMODE":

        logger.debug("Creating config-consensus.batch for Devmode")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create --key {key_path} sawtooth.consensus.algorithm.name=Devmode sawtooth.consensus.algorithm.version=0.1 -o {tmp_path}/config-consensus.batch")
        wait_and_log(stdout, stderr)

        logger.debug("Creating genesis block for Devmode")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis {tmp_path}/config-genesis.batch {tmp_path}/config-consensus.batch")
        wait_and_log(stdout, stderr)

        logger.debug("Starting all services for Devmode")
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS validator sudo -u sawtooth sawtooth-validator -vv")
        time.sleep(5)

        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command(f"screen -dmS rest sudo -u sawtooth sawtooth-rest-api -vv --bind {config['priv_ips'][0]}:8008")

        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS settings sudo -u sawtooth settings-tp -vv")

        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("screen -dmS intkey sudo -u sawtooth intkey-tp-python -vv")

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
            stdin, stdout, stderr = ssh_clients[0].exec_command(f'{user}sawset proposal create '
                                                                f'--key {key_path} '
                                                                f'sawtooth.consensus.algorithm.name=PoET '
                                                                f'sawtooth.consensus.algorithm.version=0.1 '
                                                                f'sawtooth.poet.report_public_key_pem="$(cat /etc/sawtooth/simulator_rk_pub.pem)" '
                                                                f'sawtooth.poet.valid_enclave_measurements=$(poet enclave measurement) '
                                                                f'sawtooth.poet.valid_enclave_basenames=$(poet enclave basename) '
                                                                f'-o {tmp_path}/config-consensus.batch')
            wait_and_log(stdout, stderr)

            logger.debug("Creating poet.batch")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo poet registration create "
                                                                f"--key /etc/sawtooth/keys/validator.priv "
                                                                f"-o {tmp_path}/poet.batch")
            wait_and_log(stdout, stderr)

            logger.debug("Creating genesis block for PoET using the just created config.batches")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis "
                                                                f"{tmp_path}/config-genesis.batch "
                                                                f"{tmp_path}/config-consensus.batch "
                                                                f"{tmp_path}/poet.batch")
            wait_and_log(stdout, stderr)

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "PBFT":

            logger.debug("Creating config-consensus.batch")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create "
                                                                f"--key {key_path} "
                                                                f"sawtooth.consensus.algorithm.name=pbft "
                                                                f"sawtooth.consensus.algorithm.version=1.0 "
                                                                f"sawtooth.consensus.pbft.members='{string_pbft_peers}' "
                                                                f"-o {tmp_path}/config-consensus.batch")
            wait_and_log(stdout, stderr)

            logger.debug("Creating genesis block for PBFT using the just created config.batches")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis "
                                                                f"{tmp_path}/config-genesis.batch "
                                                                f"{tmp_path}/config-consensus.batch")
            wait_and_log(stdout, stderr)

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":

            logger.debug("Creating config-consensus.batch")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"{user}sawset proposal create "
                                                                f"--key {key_path} "
                                                                f"sawtooth.consensus.algorithm.name=raft "
                                                                f"sawtooth.consensus.algorithm.version=0.1 "
                                                                f"sawtooth.consensus.raft.peers='{string_raft_peers}' "
                                                                f"-o {tmp_path}/config-consensus.batch")
            wait_and_log(stdout, stderr)

            logger.debug("Creating genesis block for RAFT using the just created config.batches")
            stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo -u sawtooth sawadm genesis "
                                                                f"{tmp_path}/config-genesis.batch "
                                                                f"{tmp_path}/config-consensus.batch")
            wait_and_log(stdout, stderr)

    logger.info("Starting the validators")
    for index1, ip1 in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo chown -R sawtooth:sawtooth /var/lib/sawtooth")
        wait_and_log(stdout, stderr)

        peer_string = " --peering static"

        if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":
            for index2 in range(0, index1):
                if peer_string == " --peering static":
                    peer_string = peer_string + " --peers "
                else:
                    peer_string = peer_string + ","
                peer_string = peer_string + f"tcp://{config['priv_ips'][index2]}:8800"

        logger.debug(f"Starting validator with screen -dmS validator sudo -u sawtooth sawtooth-validator -vv{peer_string}")
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command(f"screen -dmS validator sudo -u sawtooth sawtooth-validator -vv{peer_string}")
        time.sleep(7)

    time.sleep(10)

    logger.info("Starting REST-API, engines, settings-tp, intkey")
    for index1, ip1 in enumerate(config['priv_ips']):

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -dmS rest sudo -u sawtooth sawtooth-rest-api -vv")

    time.sleep(5)

    for index1, ip1 in enumerate(config['priv_ips']):
        if config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "POET":

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("screen -dmS registry sudo -u sawtooth poet-validator-registry-tp -vv")
            time.sleep(5)

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("screen -dmS engine sudo -u sawtooth poet-engine -vv")

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "PBFT":

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command("screen -dmS engine sudo -u sawtooth pbft-engine -vv")

        elif config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "RAFT":

            logger.debug(f"Starting RAFT engine with screen -dmS engine sudo -u sawtooth raft-engine --connect tcp://localhost:5050 -vvv")

            channel = ssh_clients[index1].get_transport().open_session()
            channel.exec_command(f"screen -dmS engine sudo -u sawtooth raft-engine --connect tcp://localhost:5050 -vvv")

            time.sleep(5)

    time.sleep(5)

    for index1, ip1 in enumerate(config['priv_ips']):
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -dmS settings sudo -u sawtooth settings-tp -vv")

    time.sleep(5)

    for index1, ip1 in enumerate(config['priv_ips']):
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -dmS intkey sudo -u sawtooth intkey-tp-python -vv")

    time.sleep(5)

    logger.info("Waiting for 10s until all nodes have started")

    time.sleep(10)

    start_processors(config, ssh_clients, logger)
    check_network(config, ssh_clients, logger)


def sawtooth_stop(config, ssh_clients, logger):

    logger.info("Killing all sawtooth services and the benchcontract processor")
    for index, _ in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command("screen -list | grep Detached | cut -d. -f1 | awk '{print $1}' | xargs kill")
        wait_and_log(stdout, stderr)

    logger.info("Deleting ledger data")
    for index, _ in enumerate(config['priv_ips']):

        if index == 0:
            stdin, stdout, stderr = ssh_clients[index].exec_command("sudo rm -r /home/ubuntu/temp")
            wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo rm -r /var/lib/sawtooth && sudo mkdir /var/lib/sawtooth && sudo chown -R sawtooth: /var/lib/sawtooth")
        wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo rm -r /var/log/sawtooth && sudo mkdir /var/log/sawtooth && sudo chown -R sawtooth: /var/log/sawtooth")
        wait_and_log(stdout, stderr)


def sawtooth_restart(config, ssh_clients, logger):

    sawtooth_stop(config, ssh_clients, logger)
    sawtooth_start(config, ssh_clients, logger)


def start_processors(config, ssh_clients, logger):

    logger.info("Starting BenchContract on every node")
    for node, _ in enumerate(config['priv_ips']):
        channel = ssh_clients[node].get_transport().open_session()
        channel.exec_command("screen -dmS benchcontract python3 /data/processor/main.py")


def upload_processors(config, scp_clients, logger):

    dir_name = os.path.dirname(os.path.realpath(__file__))
    logger.info("Uploading benchcontract processor on each node")
    for node, _ in enumerate(config['priv_ips']):
        scp_clients[node].put(dir_name + "/processor", "/data", recursive=True)


def check_network(config, ssh_clients, logger):

    key_path = "/home/ubuntu/.sawtooth/keys/ubuntu.priv"
    boo = True

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
                    boo = False
                    logger.debug(f"Node {index} on IP {ip} has not connected properly")

            except:
                logger.info(f"Something went wrong - sawtooth peer list not working")
                boo = False

    if boo is True or config['sawtooth_settings']['sawtooth.consensus.algorithm.name'].upper() == "DEVMODE":
        logger.info(f"All nodes seem to have connected properly")

    logger.info("Adapting the sawtooth specific properties such as consensus algorithm, block time, ...")
    for key in config["sawtooth_settings"]:
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo sawset proposal create --url http://{config['priv_ips'][0]}:8008 --key {key_path} {key}={config['sawtooth_settings'][key]}")
        wait_and_log(stdout, stderr)

    logger.info("Checking whether these proposals have been adopted")
    time.sleep(10)
    stdin, stdout, stderr = ssh_clients[-1].exec_command(f"sawtooth settings list --url http://{config['priv_ips'][-1]}:8008")
    stdout2 = stdout
    logger.info("Sawtooth settings: " + "".join(stdout2.readlines()))
    wait_and_log(stdout, stderr)

    logger.info("Checking whether intkey is working on every peer by making one set operation and reading on all nodes")
    value = random.randint(0, 10000)
    key = f"val{value}"

    ssh_clients[len(config['priv_ips'])-1].exec_command(f"intkey set {key} {value} --url http://{config['priv_ips'][0]}:8008")
    time.sleep(10)
    boo1 = True
    for index, ip in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"intkey show {key} --url http://{config['priv_ips'][index]}:8008")
        out = stdout.readlines()
        try:
            if (out[0].replace("\n", "") != f"{key}: {value}"):
                boo1 = False
                logger.info(f"Node {index} on IP {ip} not working properly")
            else:
                logger.info(f"Node {index} in IP {ip} is working properly")

        except:
            logger.info("Something went wrong - sawtooth intkey is not working")
            boo1 = False

    if boo1 == True:
        logger.info("Intkey working properly on all nodes")

    if boo == True and boo1 == True:
        logger.info("Sawtooth network setup was successful")
    else:
        logger.info("Sawtooth network setup was NOT successful")
        raise Exception("Blockchain did not start properly - Omitting or repeating")
