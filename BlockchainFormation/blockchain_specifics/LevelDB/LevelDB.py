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
import time
import numpy as np
from BlockchainFormation.utils.utils import *
import sys

import hashlib


def leveldb_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the LevelDB specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    pass

def leveldb_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the LevelDB specific startup script
    :return:
    """

    dir_name = os.path.dirname(os.path.realpath(__file__))

    # the indices of the blockchain nodes
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
        sys.exit("Fatal error when performing docker swarm setup")

    scp_clients[0].put(f"{dir_name}/setup", "/home/ubuntu", recursive=True)

    channel = ssh_clients[0].get_transport().open_session()
    channel.exec_command(f"(cd setup && . ~/.profile && npm install >> ~/install.log && echo 'Success' >> ~/install.log)")
    wait_till_done(config, ssh_clients, config['ips'], 180, 10, "~/install.log", "Success", 30, logger)


    logger.info("Starting the server")

    stdin, stdout, stderr = ssh_clients[0].exec_command("echo '{\n    \"ip\": \"" + f"{config['priv_ips'][0]}" + "\"\n}' >> ~/setup/config.json")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    channel = ssh_clients[0].get_transport().open_session()
    channel.exec_command(f"(cd setup && node server.js)")




def leveldb_restart(config, logger, ssh_clients, scp_clients):

    pass