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



import os, sys
import time
import numpy as np
from BlockchainFormation.utils.utils import *



def tezos_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the tezos specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    pass


def tezos_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the tezos specific startup script
    :return:
    """

    dir_name = os.path.dirname(os.path.realpath(__file__))

    config['node_indices'] = list(range(0, config['vm_count']))

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
        # sys.exit("Fatal error when performing docker swarm setup")


    peers_string = write_peers_string(config)
    for index, _ in enumerate(config['priv_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command(f"~/tezos/tezos-node config init --data-dir ~/test --connections {len(config['priv_ips'])} --expected-pow 0 --rpc-addr {config['priv_ips'][index]}:18730 --net-addr {config['priv_ips'][index]}:19730 {peers_string}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    channel = ssh_clients[0].get_transport().open_session()
    channel.exec_command("~/tezos/tezos-node identity generate --data-dir ~/test && ~/tezos/tezos-node run --data-dir ~/test --sandbox=/home/ubuntu/genesis_pubkey.json >> ~/node.log 2>&1")
    time.sleep(30)

    stdin, stdout, stderr = ssh_clients[0].exec_command(f"~/bootstrap.sh {config['priv_ips'][0]}")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    stdin, stdout, stderr = ssh_clients[0].exec_command("pidof tezos-node")
    out = stdout.readlines()
    logger.debug(out)
    logger.debug(stderr.readlines())

    pid = out[0].replace("\n", "")
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"kill {pid}")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())


    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"~/tezos/tezos-node config init --data-dir ~/test --connections {len(config['priv_ips'])} --expected-pow 0 --rpc-addr {config['priv_ips'][index]}:18730 --net-addr {config['priv_ips'][index]}:19730 {peers_string}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    channel = ssh_clients[0].get_transport().open_session()
    channel.exec_command("~/tezos/tezos-node identity generate --data-dir ~/test && ~/tezos/tezos-node run --data-dir ~/test >> ~/node.log 2>&1")
    time.sleep(30)

    for index, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"~/import.sh {config['priv_ips'][index]}")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command(f"~/tezos/tezos-baker-004-Pt24m4xi --addr {config['priv_ips'][0]} --port 18730 run with local node /home/ubuntu/test >> ~/baker.log 2>&1")
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command(f"~/tezos/tezos-accuser-004-Pt24m4xi --addr {config['priv_ips'][0]} --port 18730 run >> ~/accuser.log 2>&1")
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command(f"~/tezos/tezos-endorser-004-Pt24m4xi --addr {config['priv_ips'][0]} --port 18730 run >> ~/endorser.log 2>&1")


    for index, _ in enumerate(config['priv_ips']):

        scp_clients.put(f"{dir_name}/setup", "/home/ubuntu", recursive=True)

        logger.info("Installing npm packages")
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command(f"(cd setup && . ~/.profile && npm install >> /home/ubuntu/setup/install.log && echo Success >> /home/ubuntu/setup/install.log)")

    status_flags = wait_till_done(config, ssh_clients, config['ips'], 180, 10, "/home/ubuntu/setup/install.log", "Success", 30, logger)
    if False in status_flags:
        raise Exception("Installation failed")

    for index, ip in enumerate(config['priv_ips']):

        logger.info("Starting the server on {ip}")
        stdin, stdout, stderr = ssh_clients[0].exec_command("echo '{\n    \"ip\": \"" + f"{config['priv_ips'][index]}" + "\"\n}' >> ~/setup/config.json")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command(f"(source /home/ubuntu/.profile && cd setup && node server.js >> /home/ubuntu/server.log)")
        logger.info(f"Server is now running on {ip}")




def write_peers_string(config):

    peers_string = "--no-bootstrap-peers"

    for index, ip in enumerate(config['priv_ips']):
        peers_string = peers_string + f" --peer {config['priv_ips'][index]}:19730"

    peers_string = peers_string + " --private-mode"
    return peers_string



def tezos_restart(config, logger, ssh_clients, scp_clients):
    """
    Runs the tezos specific restart script
    :return:
    """

    pass
