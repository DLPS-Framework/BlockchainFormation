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

    # os.mkdir(f"{config['exp_dir']}/setup")
    for index, _ in enumerate(config['priv_ips']):
        write_scripts(config, index, dir_name)

        for type in ["node", "client"]:

            scp_clients[index].put(f"{config['exp_dir']}/setup/script_{type}_{index}.sh", f"/data/tezos/src/bin_{type}/script.sh")


    for index, _ in enumerate(config['priv_ips']):
        scp_clients[index].put(f"{dir_name}/setup/make.sh", "/data/tezos")
        ssh_clients[index].exec_command("eval $(opam env --switch=/data/tezos --set-switch) && cd /data/tezos && make install >> /data/make2.log 2>&1 && source /data/tezos/src/bin_client/bash-completion.sh && echo 'Hallo' >> /data/success.log")

    status_flags = wait_till_done(config, ssh_clients, config['ips'], 900, 10, "/data/success.log", "Hallo", 600, logger)
    if False in status_flags:
        raise Exception("At least one compilation was not successfull")


    for index, _ in enumerate(config['priv_ips']):
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command(f"(eval $(opam env --switch=/data/tezos --set-switch) && cd /data/tezos/src/bin_node && chmod 777 script.sh && (bash ./script.sh > /data/tezos_node.log) && (which tezos-node > /data/which.log))")

    time.sleep(5*len(config['priv_ips']))
    # wait_till_done (überall steht etwas von Worker in /data/tezos_node.log)

    for index, ip in enumerate(config['ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"(eval $(opam env --switch=/data/tezos --set-switch) && cd /data/tezos/src/bin_client && chmod 777 script.sh && (bash ./script.sh > /data/tezos_client.log) && which tezos-client)")
        out = stdout.readlines()
        logger.info(f"out on node {index} @ {ip} : {out}")
        logger.info(stderr.readlines())



def write_peers_string(config):

    peers_string = 'peers=("--no-bootstrap-peers")'
    for index, ip in enumerate(config['priv_ips']):
        peers_string = peers_string + f'; peers+=("--peer")'
        peers_string = peers_string + f'; peers+=("{ip}:19730")'

    peers_string = peers_string + '; peers+=("--private-mode")'
    return peers_string

def write_scripts(config, index, dir_name):

    for type in ["node", "client"]:

        os.system(f"cp {dir_name}/setup/tezos-sandboxed-{type}_raw.sh {config['exp_dir']}/setup/script_{type}_{index}.sh")
        n = len(config['priv_ips'])
        string_peers = write_peers_string(config)
        priv_ip = config['priv_ips'][index]

        os.system(f"sed -i -e 's/substitute_number_of_peers/{n}/g' {config['exp_dir']}/setup/script_{type}_{index}.sh")
        os.system(f"sed -i -e 's/substitute_string_peers/{string_peers}/g' {config['exp_dir']}/setup/script_{type}_{index}.sh")
        os.system(f"sed -i -e 's/substitute_priv_ip/{priv_ip}/g' {config['exp_dir']}/setup/script_{type}_{index}.sh")



def tezos_restart(config, logger, ssh_clients, scp_clients):
    """
    Runs the tezos specific restart script
    :return:
    """

    pass


def prepare(config, logger, ssh_clients, scp_clients):

    peer_string = ""
    for index, _ in enumerate(config['priv_ips']):
        peer_string = peer_string + f" --peer {config['priv_ips']}"


    for index, _ in enumerate(config['priv_ips']):
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command(f"(eval $(opam env --switch=/data/tezos --set-switch) && tezos-node run --rpc-addr {config['priv_ips'][index]} --no-bootstrap-peers --connections {len(config['priv_ips'])}{peer_string} --private-mode)")

        stdin, stdout, stderr = ssh_clients[index].exec_command(f"tezos-client --addr {config['priv_ips'][index]} --port 9732 rpc get /chains/main/blocks/head/metadata")
        wait_and_log(stdout, stderr)