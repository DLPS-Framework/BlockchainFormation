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
import sys

from BlockchainFormation.utils.utils import *


def eos_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the eos specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    pass


def eos_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the tezos specific startup script
    :return:
    """

    dir_name = os.path.dirname(os.path.realpath(__file__))

    # the indices of the blockchain nodes
    config['node_indices'] = list(range(1, config['vm_count']))

    # create directories for the fabric logs and all the setup data (crypto-stuff, config files and scripts which are exchanged with the VMs)
    os.mkdir(f"{config['exp_dir']}/eos_logs")

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

    config['join_command'] = "sudo " + join_command

    for index, _ in enumerate(config['priv_ips']):

        if index != 0:
            stdin, stdout, stderr = ssh_clients[index].exec_command("sudo " + join_command)
            out = stdout.readlines()
            # logger.debug(out)
            # logger.debug("".join(stderr.readlines()))

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

    # Starting Eos
    passwords = []

    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("cleos wallet create --name=mywallet --to-console | tail -n 1")
        out = stdout.readlines()
        logger.debug(out)
        logger.debug(stderr.readlines())

        passwords.append(out[0].replace("\n", ""))

    logger.info(f"Wallet passwords: {passwords}")

    priv_keys = []
    pub_keys = []

    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command("cleos create key --to-console")
        out = stdout.readlines()
        logger.debug(out)
        logger.debug(stdout.readlines())

        priv_keys.append(out[0].replace("\n", "").replace("Private key: ", ""))
        pub_keys.append(out[1].replace("\n", "").replace("Public key: ", ""))

        logger.info("Unlocking the wallet")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos wallet unlock --name=mywallet --password={passwords[0]}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        logger.info("Importing the key to the wallet")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos wallet import --name=mywallet --private-key={priv_keys[0]}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    logger.info(f"Private keys: {priv_keys}")
    logger.info(f"Public keys: {pub_keys}")

    config['priv_keys'] = priv_keys
    config['pub_keys'] = pub_keys

    for index, _ in enumerate(config['priv_ips']):

        logger.info("Replacing the relevant parts of the genesis block")
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"sed -i -e 's/EOS_PUB_DEV_KEY/{pub_keys[0]}/g' /data/bootbios/genesis.json")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        logger.info("Replacing the relevant keys of the genesis start script")
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"sed -i -e 's/EOS_PUB_DEV_KEY/{pub_keys[index]}/g' /data/bootbios/genesis/genesis_start.sh /data/bootbios/genesis/start.sh && sed -i -e 's/EOS_PRIV_DEV_KEY/{priv_keys[index]}/g' /data/bootbios/genesis/genesis_start.sh /data/bootbios/genesis/start.sh")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        logger.info("Replacing the relevant producer names")

        if index == 0:
            producer_name = "eosio"
        else:
            producer_name = f"producer{index}"

        stdin, stdout, stderr = ssh_clients[index].exec_command(f"sed -i -e 's/substitute_producer_name/{producer_name}/g' /data/bootbios/genesis/genesis_start.sh /data/bootbios/genesis/start.sh")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        peer_string = ""
        for index2, ip2 in enumerate(config['priv_ips']):
            if index2 != index:
                peer_string = peer_string + f"--p2p-peer-address {ip2}:4444 "

        logger.info("Giving the addresses of the other peers")
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"sed -i -e 's/substitute_peers/{peer_string}/g' /data/bootbios/genesis/genesis_start.sh /data/bootbios/genesis/start.sh")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    for index, _ in enumerate(config['priv_ips']):
        logger.info("Running the start script")
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command("(cd /data/bootbios/genesis && ./genesis_start.sh >> ~/genesis_start.log)")

    time.sleep(10)

    account_keys = {}

    # Starting the protocol by installing all associated system contracts

    for account in ["eosio.bpay", "eosio.msig", "eosio.names", "eosio.ram", "eosio.ramfee", "eosio.saving", "eosio.stake", "eosio.token", "eosio.vpay", "eosio.rex"]:
        stdin, stdout, stderr = ssh_clients[0].exec_command("cleos create key --to-console")
        out = stdout.readlines()
        logger.debug(out)
        logger.debug(stderr.readlines())

        account_keys["account"] = {}
        account_keys["account"]["priv"] = (out[0].replace("\n", "").replace("Private key: ", ""))
        account_keys["account"]["pub"] = (out[1].replace("\n", "").replace("Public key: ", ""))

        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos wallet import -n mywallet --private-key={account_keys['account']['priv']}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos create account eosio {account} {account_keys['account']['pub']}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    logger.info("All accounts successfully created")
    logger.info("Getting the contract binaries")

    if config['instance_type'] == "m5.large":

        logger.info("Uploading the compiled binaries (compiling seems to work only with >= 4 vCPUs)")
        scp_clients[0].put(f"{dir_name}/contracts", "/home/ubuntu", recursive=True)

    else:

        logger.info("Compiling the conctracts on the vm")
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("(cd ~/contracts && ./build.sh -e /usr/opt/eosio/2.0.3 -c /usr/opt/eosio.cdt/1.6.3 >> ~/deploy_contracts.log 2>&1 && touch ~/success.log)")

        time.sleep(60)

    stdin, stdout, stderr = ssh_clients[0].exec_command("cleos set contract eosio.token ~/contracts/build/contracts/eosio.token/")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    stdin, stdout, stderr = ssh_clients[0].exec_command("cleos set contract eosio.msig ~/contracts/build/contracts/eosio.msig/")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    stdin, stdout, stderr = ssh_clients[0].exec_command("cleos push action eosio.token create '[ \"eosio\", \"10000000000.0000 SYS\" ]' -p eosio.token@active && cleos push action eosio.token issue '[ \"eosio\", \"1000000000.0000 SYS\", \"memo\" ]' -p eosio@active")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    stdin, stdout, stderr = ssh_clients[0].exec_command("curl -X POST http://127.0.0.1:8888/v1/producer/get_supported_protocol_features -d '{}' | jq")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    stdin, stdout, stderr = ssh_clients[0].exec_command("curl -X POST http://127.0.0.1:8888/v1/producer/schedule_protocol_feature_activations -d '{\"protocol_features_to_activate\": [\"0ec7e080177b2c02b278d5088611686b49d739925a92d9bfcacd7fc6b74053bd\"]}' | jq")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    time.sleep(2)

    stdin, stdout, stderr = ssh_clients[0].exec_command("cleos set contract eosio contracts/build/contracts/eosio.bios -p eosio "
                                                        "&& cleos push action eosio activate '[\"f0af56d2c5a48d60a4a5b5c903edfb7db3a736a94ed589d0b797df33ff9d3e1d\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"2652f5f96006294109b3dd0bbde63693f55324af452b799ee137a81a905eed25\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"8ba52fe7a3956c5cd3a656a3174b931d3bb2abb45578befc59f283ecd816a405\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"ad9e3d8f650687709fd68f4b90b41f7d825a365b02c23a636cef88ac2ac00c43\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"68dcaa34c0517d19666e6b33add67351d8c5f69e999ca1e37931bc410a297428\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"e0fb64b1085cc5538970158d05a009c24e276fb94e1a0bf6a528b48fbc4ff526\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"ef43112c6543b88db2283a2e077278c315ae2c84719a8b25f25cc88565fbea99\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"4a90c00d55454dc5b059055ca213579c6ea856967712a56017487886a4d4cc0f\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"1a99a59d87e06e09ec5b028a9cbb7749b4a5ad8819004365d02dc4379a8b7241\"]' -p eosio "
                                                        "&& cleos push action eosio activate '[\"4e7bf348da00a945489b2a681749eb56f5de00b900014e137ddae39f48f69d67\"]' -p eosio ")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    # Trying to install the system contract multiple times because it often does not work at the first time
    for i in range(0, 3):
        logger.info(f"{i + 1}th try to install the system contract")
        stdin, stdout, stderr = ssh_clients[0].exec_command("cleos set contract eosio ~/contracts/build/contracts/eosio.system")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        time.sleep(5)

    stdin, stdout, stderr = ssh_clients[0].exec_command("(cleos push action eosio setpriv '[\"eosio.msig\", 1]' -p eosio@active && cleos push action eosio init '[\"0\", \"4,SYS\"]' -p eosio@active)")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    for index, node in enumerate(config['node_indices']):
        logger.info(f"Importing the private key of producer{index + 1} to the wallet on the eosio node")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos wallet import --name=mywallet --private-key={priv_keys[node]}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos system newaccount eosio --transfer producer{node} {pub_keys[node]} --stake-net \"100000000.0000 SYS\" --stake-cpu \"100000000.0000 SYS\" --buy-ram-kbytes 8192")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos system regproducer producer{node} {pub_keys[node]}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    time.sleep(2)

    # Staking in order to have all nodes as validators
    for index, node in enumerate(config['node_indices']):
        logger.info("Sending SYS token to the producer")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos transfer eosio producer{node} \"1000000 SYS\" \"Hallo\"")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        time.sleep(2)

        logger.info("Getting the current balance")
        stdin, stdout, stderr = ssh_clients[node].exec_command(f"cleos get currency balance eosio.token producer{node} SYS")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        time.sleep(2)

        logger.info("Staking...")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos system delegatebw producer{node} producer{node} \"20 SYS\" \"20 SYS\"")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        time.sleep(2)

        logger.info("Voting...")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"cleos system voteproducer prods producer{node} producer{node}")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

    stdin, stdout, stderr = ssh_clients[0].exec_command("cleos system listproducers")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))


def eos_restart(config, logger, ssh_clients, scp_clients):
    """
    Runs the eos specific restart script
    :return:
    """

    pass


def eos_check_config(config, logger):
    logger.debug(f"Modifying the eos config")
    config['vm_count'] = config['vm_count'] + 1

    if config['eos_settings']['block_interval_ms'] != 500:

        if config['instance_type'] not in ["m5.large", "m5.2xlarge", "m5.4xlarge", "m5.8xlarge"]:
            logger.error("For non-default eos-settings, we need at least 8 GB of RAM")
            raise Exception()

        return True

    else:
        return False
