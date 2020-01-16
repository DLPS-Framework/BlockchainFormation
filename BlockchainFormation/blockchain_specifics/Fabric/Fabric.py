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



import boto3
import json
import numpy as np
import os
import paramiko
import subprocess
import sys
import time
from scp import SCPClient
from BlockchainFormation import vm_handler
from BlockchainFormation.utils.utils import *

import threading


def fabric_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the fabric specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    # for index, _ in enumerate(config['priv_ips']):
        # scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs")
        # scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

    # the indices of the different roles
    config['orderer_indices'] = list(range(0, config['fabric_settings']['orderer_count']))
    config['peer_indices'] = list(range(config['fabric_settings']['orderer_count'], config['fabric_settings']['orderer_count'] + config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count']))

    if config['fabric_settings']['orderer_type'].upper() == "KAFKA":
        config['zookeeper_indices'] = list(range(config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'], config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count']))
        config['kafka_indices'] = list(range(config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'], config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'] + config['fabric_settings']['kafka_count']))
    else:
        config['zookeeper_indices'] = []
        config['kafka_indices'] = []

    for index, _ in enumerate(ssh_clients):
        stdin, stdout, stderr = ssh_clients[index].exec_command("docker stop $(docker ps -a -q) && docker rm -f $(docker ps -a -q) && docker rmi $(docker images | grep 'my-net' | awk '{print $1}')")
        stdout.readlines()
        # logger.debug(stdout.readlines())
        # logger.debug(stderr.readlines())
        stdin, stdout, stderr = ssh_clients[index].exec_command("docker volume rm $(docker volume ls -q)")
        stdout.readlines()
        # logger.debug(stdout.readlines())
        # logger.debug(stderr.readlines())
        stdin, stdout, stderr = ssh_clients[index].exec_command("docker ps -a && docker volume ls && docker images")
        stdout.readlines()
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

    """

    for index, _ in enumerate(ssh_clients):
        ssh_clients[index].exec_command("sudo reboot")

    logger.info("Waiting till all machines have rebooted")
    time.sleep(10)

    status_flags = wait_till_done(config, ssh_clients, config['ips'], 10*60, 10, "/var/log/user_data_success.log", False, 10*60, logger)

    stdin, stdout, stderr = ssh_clients[index].exec_command("docker volume rm $(docker volume ls -q)")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    stdin, stdout, stderr = ssh_clients[index].exec_command("docker ps -a && docker volume ls ")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    """


def fabric_startup(config, logger, ssh_clients, scp_clients):

    dir_name = os.path.dirname(os.path.realpath(__file__))

    # the indices of the different roles
    config['orderer_indices'] = list(range(0, config['fabric_settings']['orderer_count']))
    config['peer_indices'] = list(range(config['fabric_settings']['orderer_count'], config['fabric_settings']['orderer_count'] + config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count']))

    if config['fabric_settings']['orderer_type'].upper() == "KAFKA":
        config['zookeeper_indices'] = list(range(config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'], config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count']))
        config['kafka_indices'] = list(range(config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'], config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'] + config['fabric_settings']['kafka_count']))
    else:
        config['zookeeper_indices'] = []
        config['kafka_indices'] = []

    # the indices of the blockchain nodes
    config['node_indices'] = config['peer_indices']

    # create directories for the fabric logs and all the setup data (crypto-stuff, config files and scripts which are exchanged with the VMs)
    os.mkdir(f"{config['exp_dir']}/fabric_logs")
    os.mkdir(f"{config['exp_dir']}/api")

    # Rebooting all machines
    # ssh_clients, scp_clients = reboot_all(ec2_instances, config, logger, ssh_clients, scp_clients)

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
        sys.exit("Fatal error when performing docker swarm setup")

    logger.info(f"Creating crypto-config.yaml and pushing it to {config['ips'][0]}")
    write_crypto_config(config, logger)

    stdin, stdout, stderr = ssh_clients[0].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config.yaml")
    stdout.readlines()
    # logger.debug("".join(stdout.readlines()))
    # logger.debug("".join(stderr.readlines()))f
    scp_clients[0].put(f"{config['exp_dir']}/setup/crypto-config.yaml", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config.yaml")

    logger.info(f"Creating configtx and pushing it to {config['ips'][0]}")
    write_configtx(config, logger)
    # os.system(f"cp {dir_name}/setup/configtx.yaml {config['exp_dir']}/setup/configtx.yaml")
    stdin, stdout, stderr = ssh_clients[0].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/configtx.yaml")
    stdout.readlines()
    # logger.debug("".join(stdout.readlines()))
    # logger.debug("".join(stderr.readlines()))
    scp_clients[0].put(f"{config['exp_dir']}/setup/configtx.yaml", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/configtx.yaml")

    stdin, stdout, stderr = ssh_clients[-1].exec_command("which configtxgen")
    out = stdout.readlines()
    logger.debug("Configtxgen version")
    logger.debug(out)
    logger.debug(stderr.readlines())

    logger.info(f"Creating bmhn.sh and pushing it to {config['ips'][0]}")
    os.system(f"cp {dir_name}/setup/bmhn_raw.sh {config['exp_dir']}/setup/bmhn.sh")
    enum_orgs = "1"
    for org in range(2, config['fabric_settings']['org_count'] + 1):
        enum_orgs = enum_orgs + f" {org}"

    os.system(f"sed -i -e 's/substitute_enum_orgs/{enum_orgs}/g' {config['exp_dir']}/setup/bmhn.sh")
    stdin, stdout, stderr = ssh_clients[0].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/bmhn.sh")
    stdout.readlines()
    # logger.debug("".join(stdout.readlines()))
    # logger.debug("".join(stderr.readlines()))
    scp_clients[0].put(f"{config['exp_dir']}/setup/bmhn.sh", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/bmhn.sh")

    logger.info(f"Creating crypto-stuff on {config['ips'][0]} by executing bmhn.sh")
    stdin, stdout, stderr = ssh_clients[0].exec_command("rm -rf /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config")
    stdout.readlines()
    # logger.debug("".join(stdout.readlines()))
    # logger.debug("".join(stderr.readlines()))

    stdin, stdout, stderr = ssh_clients[0].exec_command("( cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo y | bash ./bmhn.sh )")
    out = stdout.readlines()
    for index, _ in enumerate(out):
        logger.debug(out[index].replace("\n", ""))

    logger.debug("".join(stderr.readlines()))

    logger.info(f"Getting crypto-config and channel-artifacts from {config['ips'][0]}...")
    scp_clients[0].get("/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config", f"{config['exp_dir']}/setup", recursive=True)
    scp_clients[0].get("/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts", f"{config['exp_dir']}/setup", recursive=True)

    logger.info("Pushing crypto-config, channel-artifacts, and chaincode to all remaining other nodes")
    indices = config['orderer_indices'] + config['peer_indices']

    # pushing the ssh-key and the chaincode on the first vm
    scp_clients[0].put(f"{config['priv_key_path']}", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem")
    scp_clients[0].put(f"{dir_name}/chaincode/benchcontract", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode", recursive=True)
    logger.debug("Successfully pushed to index 0.")

    finished_indices = [indices[0]]
    remaining_indices = indices[1:len(indices)]
    while remaining_indices != []:
        n_targets = min(len(finished_indices), len(remaining_indices))
        indices_sources = finished_indices[0:n_targets]
        indices_targets = remaining_indices[0:n_targets]

        push_stuff(config, ssh_clients, scp_clients, indices_sources, indices_targets, logger)

        finished_indices = indices_sources + indices_targets
        remaining_indices = remaining_indices[n_targets:]

    # deleting the ssh-keys after having finished
    for _, index in enumerate(indices):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"rm /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem")
        stdout.readlines()

    # with concurrent.futures.ProcessPoolExecutor() as executor:
        # for _ in executor.map(push_stuff, repeat(config), repeat(ssh_clients), repeat(scp_clients), repeat(dir_name), pushing_indices, repeat(logger)):
            # print(_)

    # processed_list = Parallel(n_jobs=num_cores)(delayed(push_stuff)(config, ssh_clients, scp_clients, dir_name, i, logger) for i in inputs)
    # logger.debug(f"Process list: {processed_list}")

    # pool = multiprocessing.Pool(multiprocessing.cpu_count())
    # results = [pool.apply(push_stuff, args=(config, ssh_clients, scp_clients, dir_name, index, logger)) for index in inputs]

    # pool.close()
    # logger.debug(results)

    start_docker_containers(config, logger, ssh_clients, scp_clients)

    logger.info("Getting logs from vms")

    for index, ip in enumerate(config['ips']):
        scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

    try:
        scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs")
        logger.info("Logs fetched successfully")
    except:
        logger.info(f"No logs available on {ip}")

    logger.info("")


def reboot_all(ec2_instances, config, logger, ssh_clients, scp_clients):
    """
    Restart Fabric Network
    :param ec2_instances:
    :param config:
    :param logger:
    :param ssh_clients:
    :param scp_clients:
    :return:
    """
    status_flags = np.zeros((config['vm_count']), dtype=bool)
    timer = 4
    logger.info("   ###              ***               ###")
    logger.info("  ###    Rebooting all Fabric-VMs      ###")
    logger.info("   ###              ***               ###")
    for i in ec2_instances:
        i.reboot()

    time.sleep(90)
    logger.info("Waiting for all VMs to finish reboot...")
    while (False in status_flags and timer < 30):
        # logger.info(f"Waited {timer * 40} seconds so far, {300 - timer * 20} seconds left before abort (it usually takes around 2 minutes)")
        ssh_key_priv = paramiko.RSAKey.from_private_key_file(config['priv_key_path'])
        for index, ip in enumerate(config['ips']):
            if (status_flags[index] == False):
                try:
                    ssh_clients[index].connect(hostname=ip, username=config['user'], pkey=ssh_key_priv)
                    scp_clients[index] = SCPClient(ssh_clients[index].get_transport())
                    status_flags[index] = True
                except:
                    timer += 1
                    logger.info(f"{ip} not ready")

    logger.info("Rebooting completed")
    return ssh_clients, scp_clients


def write_crypto_config(config, logger):
    dir_name = os.path.dirname(os.path.realpath(__file__))

    f = open(f"{config['exp_dir']}/setup/crypto-config.yaml", "w+")

    f.write(f"# Copyright IBM Corp. All Rights Reserved.\n")
    f.write(f"#\n")
    f.write(f"# SPDX-License-Identifier: Apache-2.0\n")
    f.write(f"#\n")
    f.write(f"\n")
    f.write(f"# Orderer organizations\n")
    f.write(f"OrdererOrgs:\n")
    f.write(f"\n")
    f.write(f"    - Name: Orderer\n")
    f.write(f"      Domain: example.com\n")
    f.write(f"\n")
    f.write(f"      Template:\n")
    f.write(f"          Count: {config['fabric_settings']['orderer_count']}\n")
    f.write(f"          Start: 1\n")
    # f.write(f"      Specs:\n")
    # f.write(f"        - Hostname: orderer\n")
    f.write(f"\n")
    f.write(f"# Peer Organizations\n")
    f.write(f"PeerOrgs:\n")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        f.write(f"    - Name: Org{org}\n")
        f.write(f"      Domain: org{org}.example.com\n")
        f.write(f"      Template:\n")
        f.write(f"          # The number of peers in this organization\n")
        f.write(f"          Count: {config['fabric_settings']['peer_count']}\n")
        f.write(f"      Users:\n")
        f.write(f"          # The number of users in this organization\n")
        f.write(f"          Count: 1\n")
        f.write(f"\n")

    f.close()


def write_configtx(config, logger):
    dir_name = os.path.dirname(os.path.realpath(__file__))

    f = open(f"{config['exp_dir']}/setup/configtx.yaml", "w+")

    enum_MSP_members = "('OrdererMSP.member', 'Org1MSP.member'"
    for org in range(2, config['fabric_settings']['org_count'] + 1):
        enum_MSP_members = enum_MSP_members + f", 'Org{org}MSP.member'"

    enum_MSP_members = enum_MSP_members + ")"

    endorsement = "\"OR" + enum_MSP_members + "\""

    f.write(f"# Copyright IBM Corp. All Rights Reserved.\n")
    f.write(f"#\n")
    f.write(f"# SPDX-License-Identifier: Apache-2.0\n")
    f.write(f"#\n")
    f.write(f"\n")
    f.write(f"################################################################################\n")
    f.write(f"#\n")
    f.write(f"#   SECTION: Capabilities\n")
    f.write(f"#\n")
    f.write(f"#   - This section defines the capabilities of fabric network. This is a new\n")
    f.write(f"#   concept as of v1.1.0 and should not be utilized in mixed networks with\n")
    f.write(f"#   v1.0.x peers and orderers.  Capabilities define features which must be\n")
    f.write(f"#   present in a fabric binary for that binary to safely participate in the\n")
    f.write(f"#   fabric network.  For instance, if a new MSP type is added, newer binaries\n")
    f.write(f"#   might recognize and validate the signatures from this type, while older\n")
    f.write(f"#   binaries without this support would be unable to validate those\n")
    f.write(f"#   transactions.  This could lead to different versions of the fabric binaries\n")
    f.write(f"#   having different world states.  Instead, defining a capability for a channel\n")
    f.write(f"#   informs those binaries without this capability that they must cease\n")
    f.write(f"#   processing transactions until they have been upgraded.  For v1.0.x if any\n")
    f.write(f"#   capabilities are defined (including a map with all capabilities turned off)\n")
    f.write(f"#   then the v1.0.x peer will deliberately crash.\n")
    f.write(f"#\n")
    f.write(f"################################################################################\n")
    f.write(f"\n")
    f.write(f"Capabilities:\n")
    f.write(f"    # Channel capabilities apply to both the orderers and the peers and must be\n")
    f.write(f"    # supported by both.  Set the value of the capability to true to require it.\n")
    f.write(f"    Global: &ChannelCapabilities\n")
    f.write(f"        # V1.1 for Global is a catchall flag for behavior which has been\n")
    f.write(f"        # determined to be desired for all orderers and peers running v1.0.x,\n")
    f.write(f"        # but the modification of which would cause incompatibilities.  Users\n")
    f.write(f"        # should leave this flag set to true.\n")
    f.write(f"        # V1_4_3: true\n")
    f.write(f"        # V1_3: false\n")
    f.write(f"        V1_1: true\n")
    f.write(f"\n")
    f.write(f"    # Orderer capabilities apply only to the orderers, and may be safely\n")
    f.write(f"    # manipulated without concern for upgrading peers.  Set the value of the\n")
    f.write(f"    # capability to true to require it.\n")
    f.write(f"    Orderer: &OrdererCapabilities\n")
    f.write(f"        # V1.1 for Order is a catchall flag for behavior which has been\n")
    f.write(f"        # determined to be desired for all orderers running v1.0.x, but the\n")
    f.write(f"        # modification of which  would cause incompatibilities.  Users should\n")
    f.write(f"        # leave this flag set to true.\n")
    f.write(f"        # V1_4_2: true\n")
    f.write(f"        V1_1: true\n")
    f.write(f"\n")
    f.write(f"    # Application capabilities apply only to the peer network, and may be safely\n")
    f.write(f"    # manipulated without concern for upgrading orderers.  Set the value of the\n")
    f.write(f"    # capability to 'true' to require it.\n")
    f.write(f"    Application: &ApplicationCapabilities\n")
    f.write(f"        # V1.2 for Application is a catchall flag for behavior which has been\n")
    f.write(f"        # determined to be desired for all peers running v1.0.x, but the\n")
    f.write(f"        # modification of which would cause incompatibilities.  Users should\n")
    f.write(f"        # leave this flag set to 'true'.\n")
    f.write(f"        V1_2: true\n")
    f.write(f"\n")
    f.write(f"\n")
    f.write(f"\n")
    f.write(f"################################################################################\n")
    f.write(f"#\n")
    f.write(f"#   Section: Organizations\n")
    f.write(f"#\n")
    f.write(f"#   - This section defines the different organizational identities which will\n")
    f.write(f"#   be referenced later in the configuration.\n")
    f.write(f"#\n")
    f.write(f"################################################################################\n")
    f.write(f"\n")
    f.write(f"Organizations:\n")
    f.write(f"\n")
    f.write(f"    - &OrdererOrg\n")
    f.write(f"        Name: OrdererOrg\n")
    f.write(f"        ID: OrdererMSP\n")
    f.write(f"        MSPDir: crypto-config/ordererOrganizations/example.com/msp\n")
    f.write(f"        Policies: &OrdererOrgPolicies\n")
    f.write(f"            Readers:\n")
    f.write(f"                Type: Signature\n")
    f.write(f"                Rule: \"OR('OrdererMSP.member')\"\n")
    f.write(f"            # If your MSP is configured with the new NodeOUs, you might\n")
    f.write(f"            # want to use a more specific rule like the following:\n")
    f.write(f"            # Rule: \"OR('OrdererMSP.admin', 'Org1MSP.admin', 'Org2MSP.admin')\"\n")
    f.write(f"            Writers:\n")
    f.write(f"                Type: Signature\n")
    f.write(f"                Rule: \"OR('OrdererMSP.member')\"\n")
    f.write(f"            # If your MSP is configured with the new NodeOUs, you might\n")
    f.write(f"            # want to use a more specific rule like the following:\n")
    f.write(f"            # Rule: \"OR('OrdererMSP.admin', 'Org1MSP.admin', 'Org2MSP.admin')\"\n")
    f.write(f"            Admins:\n")
    f.write(f"                Type: Signature\n")
    f.write(f"                Rule: \"OR('OrdererMSP.member')\"\n")
    f.write(f"\n")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        f.write(f"    - &Org{org}\n")
        f.write(f"        Name: Org{org}MSP\n")
        f.write(f"        ID: Org{org}MSP\n")
        f.write(f"        MSPDir: crypto-config/peerOrganizations/org{org}.example.com/msp\n")
        f.write(f"        AnchorPeers:\n")
        f.write(f"            - Host: peer0.org{org}.example.com\n")
        f.write(f"              Port: 7051\n")
        f.write(f"        Policies: &Org{org}Policies\n")
        f.write(f"            Readers:\n")
        f.write(f"                Type: Signature\n")
        f.write(f"                Rule: \"OR('Org{org}MSP.member')\"\n")
        f.write(f"            Writers:\n")
        f.write(f"                Type: Signature\n")
        f.write(f"                Rule: \"OR('Org{org}MSP.member')\"\n")
        f.write(f"            Admins:\n")
        f.write(f"                Type: Signature\n")
        f.write(f"                Rule: \"OR('Org{org}.admin')\"\n")
        f.write(f"            Endorsement:\n")
        f.write(f"                Type: Signature\n")
        f.write(f"                Rule: \"OR('Org{org}MSP.member')\"\n")
        f.write(f"\n")
    f.write(f"\n")
    f.write(f"################################################################################\n")
    f.write(f"#\n")
    f.write(f"#   SECTION: Orderer\n")
    f.write(f"#\n")
    f.write(f"#   - This section defines the values to encode into a config transaction or\n")
    f.write(f"#   genesis block for orderer related parameters\n")
    f.write(f"#\n")
    f.write(f"################################################################################\n")
    f.write(f"\n")
    f.write(f"Orderer: &OrdererDefaults\n")
    f.write(f"\n")
    f.write(f"# Orderer Type: The orderer implementation to start\n")
    f.write(f"# Available types are 'solo', 'kafka' and 'etcdraft'\n")

    if config['fabric_settings']['orderer_type'].upper() == "RAFT":

        if config['fabric_settings']['tls_enabled'] != 1:
            sys.exit("RAFT is only supported with TLS enabled")

        f.write("\n    OrdererType: etcdraft\n\n")

        f.write("    EtcdRaft:\n")
        f.write("        Consenters:\n")
        for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
            f.write(f"            - Host: orderer{orderer}.example.com\n")
            f.write(f"              Port: 7050\n")
            f.write(f"              ClientTLSCert: crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls/server.crt\n")
            f.write(f"              ServerTLSCert: crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls/server.crt\n")

        f.write(f"\n")
        f.write(f"\n")
        f.write(f"        # Options to be specified for all the etcd/raft nodes. The values here\n")
        f.write(f"        # are the defaults for all new channels and can be modified on a\n")
        f.write(f"        # per-channel basis via configuration updates.\n")
        f.write(f"        Options:\n")
        f.write(f"\n")
        f.write(f"            # TickInterval is the time interval between two Node.Tick invocations.\n")
        f.write(f"            TickInterval: {config['fabric_settings']['tick_interval']}ms\n")
        f.write(f"\n")
        f.write(f"            # ElectionTick is the number of Node.Tick invocations that must pass\n")
        f.write(f"            # between elections. That is, if a follower does not receive any\n")
        f.write(f"            # message from the leader of current term before ElectionTick has\n")
        f.write(f"            # elapsed, it will become candidate and start an election.\n")
        f.write(f"            # ElectionTick must be greater than HeartbeatTick.\n")
        f.write(f"            ElectionTick: {config['fabric_settings']['election_tick']}\n")
        f.write(f"\n")
        f.write(f"            # HeartbeatTick is the number of Node.Tick invocations that must\n")
        f.write(f"            # pass between heartbeats. That is, a leader sends heartbeat\n")
        f.write(f"            # messages to maintain its leadership every HeartbeatTick ticks.\n")
        f.write(f"            HeartbeatTick: {config['fabric_settings']['heartbeat_tick']}\n")
        f.write(f"\n")
        f.write(f"            # MaxInflightBlocks limits the max number of in-flight append messages\n")
        f.write(f"            # during optimistic replication phase.\n")
        f.write(f"            MaxInflightBlocks: {config['fabric_settings']['max_inflight_locks']}\n")
        f.write(f"\n")
        f.write(f"            # SnapshotIntervalSize defines number of bytes per which a snapshot is taken\n")
        f.write(f"            SnapshotIntervalSize: {config['fabric_settings']['snapshot_interval_size']} MB\n")
        f.write(f"\n")
        f.write(f"\n")

    elif config['fabric_settings']['orderer_type'].upper() == "KAFKA":
        f.write("\n    OrdererType: kafka\n\n")

        f.write("    Kafka:\n")
        f.write("        Brokers:\n")
        for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
            f.write(f"            - kafka{orderer-1}:9092\n")

    elif config['fabric_settings']['orderer_type'].upper() == "SOLO":
        f.write("\n    OrdererType: solo\n\n")

    else:
        sys.exit(f"The orderer type {config['fabric_settings']['orderer_type']} is not supported")

    f.write("\n")
    f.write("    Addresses:\n")
    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        f.write(f"        - orderer{orderer}.example.com:7050\n")
        
    f.write(f"\n")
    f.write(f"    # Batch Timeout: The amount of time to wait before creating a batch\n")
    f.write(f"    BatchTimeout: {config['fabric_settings']['batch_timeout']}s\n")
    f.write(f"    # Batch Size: Controls the number of messages batched into a block\n")
    f.write(f"    BatchSize:\n")
    f.write(f"\n")
    f.write(f"        # Max Message Count: The maximum number of messages to permit in a batch\n")
    f.write(f"        MaxMessageCount: {config['fabric_settings']['max_message_count']}\n")
    f.write(f"\n")
    f.write(f"        # Absolute Max Bytes: The absolute maximum number of bytes allowed for\n")
    f.write(f"        # the serialized messages in a batch.\n")
    f.write(f"        AbsoluteMaxBytes: {config['fabric_settings']['absolute_max_bytes']} MB\n")
    f.write(f"\n")
    f.write(f"        # Preferred Max Bytes: The preferred maximum number of bytes allowed for\n")
    f.write(f"        # the serialized messages in a batch. A message larger than the preferred\n")
    f.write(f"        # max bytes will result in a batch larger than preferred max bytes.\n")
    f.write(f"        PreferredMaxBytes: {config['fabric_settings']['preferred_max_bytes']} KB\n")
    f.write(f"\n")
    f.write(f"    # Organizations is the list of orgs which are defined as participants on\n")
    f.write(f"    # the orderer side of the network\n")
    f.write(f"    Organizations:\n")
    f.write(f"\n")
    f.write(f"    Policies:\n")
    f.write(f"        Readers:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        Writers:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        Admins:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        # BlockValidation specifies what signatures must be included in the block\n")
    f.write(f"        # from the orderer for the peer to validate it.\n")
    f.write(f"        BlockValidation:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"\n")
    f.write(f"    # Capabilities describes the orderer level capabilities, see the\n")
    f.write(f"    # dedicated Capabilities section elsewhere in this file for a full\n")
    f.write(f"    # description\n")
    f.write(f"    Capabilities:\n")
    f.write(f"        <<: *OrdererCapabilities")
    f.write(f"\n")
    f.write(f"\n")
    f.write(f"################################################################################\n")
    f.write(f"#\n")
    f.write(f"#   SECTION: Channel\n")
    f.write(f"#\n")
    f.write(f"#   This section defines the values to encode into a config transaction or\n")
    f.write(f"#   genesis block for channel related parameters.\n")
    f.write(f"#\n")
    f.write(f"################################################################################\n")
    f.write(f"\n")
    f.write(f"Channel: &ChannelDefaults\n")
    f.write(f"    # Policies defines the set of policies at this level of the config tree\n")
    f.write(f"    # For Channel policies, their canonical path is\n")
    f.write(f"    #   /Channel/<PolicyName>\n")
    f.write(f"    Policies:\n")
    f.write(f"        # Who may invoke the 'Deliver' API\n")
    f.write(f"        Readers:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        # Who may invoke the 'Broadcast' API\n")
    f.write(f"        Writers:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        # By default, who may modify elements at this config level\n")
    f.write(f"        Admins:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"\n")
    f.write(f"\n")
    f.write(f"    # Capabilities describes the channel level capabilities, see the\n")
    f.write(f"    # dedicated Capabilities section elsewhere in this file for a full\n")
    f.write(f"    # description\n")
    f.write(f"    Capabilities:\n")
    f.write(f"        <<: *ChannelCapabilities\n")
    f.write(f"\n")
    f.write(f"\n")
    f.write(f"################################################################################\n")
    f.write(f"#\n")
    f.write(f"#   SECTION: Application\n")
    f.write(f"#\n")
    f.write(f"#   - This section defines the values to encode into a config transaction or\n")
    f.write(f"#   genesis block for application related parameters\n")
    f.write(f"#\n")
    f.write(f"################################################################################\n")
    f.write(f"\n")
    f.write(f"Application: &ApplicationDefaults\n")
    f.write(f"    ACLs: &ACLsDefault\n")
    f.write(f"        # This section provides defaults for policies for various resources\n")
    f.write(f"        # in the system. These \"resources\" could be functions on system chaincodes\n")
    f.write(f"        # (e.g., \"GetBlockByNumber\" on the \"qscc\" system chaincode) or other resources\n")
    f.write(f"        # (e.g.,who can receive Block events). This section does NOT specify the resource's\n")
    f.write(f"        # definition or API, but just the ACL policy for it.\n")
    f.write(f"        #\n")
    f.write(f"        # User's can override these defaults with their own policy mapping by defining the\n")
    f.write(f"        # mapping under ACLs in their channel definition\n")
    f.write(f"\n")
    f.write(f"        #---New Lifecycle System Chaincode (_lifecycle) function to policy mapping for access control--#\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for _lifecycle's \"CommitChaincodeDefinition\" function\n")
    f.write(f"        _lifecycle/CommitChaincodeDefinition: /Channel/Application/Writers\n")
    f.write(f"        # ACL policy for _lifecycle's \"QueryChaincodeDefinition\" function\n")
    f.write(f"        _lifecycle/QueryChaincodeDefinition: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for _lifecycle's \"QueryNamespaceDefinitions\" function\n")
    f.write(f"        _lifecycle/QueryNamespaceDefinitions: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        #---Lifecycle System Chaincode (lscc) function to policy mapping for access control---#\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for lscc's \"getid\" function\n")
    f.write(f"        lscc/ChaincodeExists: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for lscc's \"getdepspec\" function\n")
    f.write(f"        lscc/GetDeploymentSpec: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for lscc's \"getccdata\" function\n")
    f.write(f"        lscc/GetChaincodeData: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL Policy for lscc's \"getchaincodes\" function\n")
    f.write(f"        lscc/GetInstantiatedChaincodes: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        #---Query System Chaincode (qscc) function to policy mapping for access control---#\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for qscc's \"GetChainInfo\" function\n")
    f.write(f"        qscc/GetChainInfo: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for qscc's \"GetBlockByNumber\" function\n")
    f.write(f"        qscc/GetBlockByNumber: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for qscc's  \"GetBlockByHash\" function\n")
    f.write(f"        qscc/GetBlockByHash: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for qscc's \"GetTransactionByID\" function\n")
    f.write(f"        qscc/GetTransactionByID: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for qscc's \"GetBlockByTxID\" function\n")
    f.write(f"        qscc/GetBlockByTxID: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        #---Configuration System Chaincode (cscc) function to policy mapping for access control---#\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for cscc's \"GetConfigBlock\" function\n")
    f.write(f"        cscc/GetConfigBlock: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for cscc's \"GetConfigTree\" function\n")
    f.write(f"        cscc/GetConfigTree: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for cscc's \"SimulateConfigTreeUpdate\" function\n")
    f.write(f"        cscc/SimulateConfigTreeUpdate: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        #---Miscellanesous peer function to policy mapping for access control---#\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for invoking chaincodes on peer\n")
    f.write(f"        peer/Propose: /Channel/Application/Writers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for chaincode to chaincode invocation\n")
    f.write(f"        peer/ChaincodeToChaincode: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        #---Events resource to policy mapping for access control###---#\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for sending block events\n")
    f.write(f"        event/Block: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"        # ACL policy for sending filtered block events\n")
    f.write(f"        event/FilteredBlock: /Channel/Application/Readers\n")
    f.write(f"\n")
    f.write(f"    # Organizations lists the orgs participating on the application side of the\n")
    f.write(f"    # network.\n")
    f.write(f"    Organizations:\n")
    f.write(f"\n")
    f.write(f"    # Policies defines the set of policies at this level of the config tree\n")
    f.write(f"    # For Application policies, their canonical path is\n")
    f.write(f"    #   /Channel/Application/<PolicyName>\n")
    f.write(f"    Policies: &ApplicationDefaultPolicies\n")
    f.write(f"        LifecycleEndorsement:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        Endorsement:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        Readers:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        Writers:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"        Admins:\n")
    f.write(f"            Type: Signature\n")
    f.write(f"            Rule: {endorsement}\n")
    f.write(f"\n")
    f.write(f"    # Capabilities describes the application level capabilities, see the\n")
    f.write(f"    # dedicated Capabilities section elsewhere in this file for a full\n")
    f.write(f"    # description\n")
    f.write(f"    Capabilities:\n")
    f.write(f"        <<: *OrdererCapabilities\n")
    f.write(f"\n")
    f.write(f"\n")
    f.write(f"################################################################################\n")
    f.write(f"#\n")
    f.write(f"#   Profile\n")
    f.write(f"#\n")
    f.write(f"#   - Different configuration profiles may be encoded here to be specified\n")
    f.write(f"#   as parameters to the configtxgen tool\n")
    f.write(f"#\n")
    f.write(f"################################################################################\n")
    f.write(f"Profiles:\n")
    f.write(f"\n")
    f.write(f"    OrdererGenesis:\n")
    f.write(f"        <<: *ChannelDefaults\n")
    f.write(f"        Capabilities:\n")
    f.write(f"            <<: *ChannelCapabilities\n")
    f.write(f"        Orderer:\n")
    f.write(f"            <<: *OrdererDefaults\n")
    f.write(f"            Organizations:\n")
    f.write(f"            - <<: *OrdererOrg\n")
    f.write(f"              Policies:\n")
    f.write(f"                  <<: *OrdererOrgPolicies\n")
    f.write(f"                  Admins:\n")
    f.write(f"                      Type: Signature\n")
    f.write(f"                      Rule: \"OR('OrdererMSP.member')\"\n")
    f.write(f"            Capabilities:\n")
    f.write(f"                - *OrdererCapabilities\n")
    f.write(f"        Consortiums:\n")
    f.write(f"            SampleConsortium:\n")
    f.write(f"                Organizations:\n")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        f.write(f"                    - <<: *Org{org}\n")
        f.write(f"                      Policies:\n")
        f.write(f"                          <<: *Org{org}Policies\n")
        f.write(f"                          Admins:\n")
        f.write(f"                              Type: Signature\n")
        f.write(f"                              Rule: \"OR('Org{org}MSP.member')\"\n")

    f.write(f"\n")
    f.write(f"    ChannelConfig:\n")
    f.write(f"        Consortium: SampleConsortium\n")
    f.write(f"        <<: *ChannelDefaults\n")
    f.write(f"        Application:\n")
    f.write(f"            <<: *ApplicationDefaults\n")
    f.write(f"            Organizations:\n")

    for org in range(1, config['fabric_settings']['org_count'] + 1):
        f.write(f"                - *Org{org}\n")

    f.write(f"            Capabilities:\n")
    f.write(f"                <<: *ApplicationCapabilities\n")


    f.close()
    

def write_script(config, logger):
    dir_name = os.path.dirname(os.path.realpath(__file__))
    os.system(
        f"cp {dir_name}/setup/script_raw_1.sh {config['exp_dir']}/setup/script.sh")

    f = open(f"{config['exp_dir']}/setup/script2.sh", "w+")

    f.write("\n\nsetGlobals() {\n\n")

    f.write("    CORE_PEER_ADDRESS=peer$1.org$2.example.com:7051\n")
    f.write("    CORE_PEER_LOCALMSPID=Org$2MSP\n")

    f.write("    CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/ca.crt\n")
    f.write("    CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/users/Admin@org$2.example.com/msp\n")

    if config['fabric_settings']['tls_enabled'] == 1:
        f.write("    # setting TLS environment variables\n")
        f.write("    CORE_PEER_TLS_ENABLED=true\n")
        f.write("    CORE_PEER_TLS_CLIENTAUTHREQUIRED=false\n")
        f.write("    CORE_PEER_TLS_CERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/server.crt\n")
        f.write("    CORE_PEER_TLS_KEY_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/server.key\n")
        f.write("    CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/ca.crt\n")
    else:
        f.write("    CORE_PEER_TLS_ENABLED=false\n")

    f.write("}\n\n")

    f.close()

    os.system(f"cp {dir_name}/setup/script_raw_3.sh {config['exp_dir']}/setup/script3.sh")
    if config['fabric_settings']['tls_enabled'] == 1:
        # logger.debug("    --> TLS environment variables set")
        string_tls = f"--tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem"
    else:
        string_tls = f""

    # append the parts of script to the final script
    os.system(f"cat {config['exp_dir']}/setup/script2.sh >> {config['exp_dir']}/setup/script.sh && rm {config['exp_dir']}/setup/script2.sh")
    os.system(f"cat {config['exp_dir']}/setup/script3.sh >> {config['exp_dir']}/setup/script.sh && rm {config['exp_dir']}/setup/script3.sh")

    # substitute the enumeration of peers and orgs
    enum_peers = "0"
    for peer in range(1, config['fabric_settings']['peer_count']):
        enum_peers = enum_peers + f" {peer}"

    enum_orgs = "1"
    for org in range(2, config['fabric_settings']['org_count'] + 1):
        enum_orgs = enum_orgs + f" {org}"

    enum_MSPmembers = " (\"'Org1MSP.member'\""
    for org in range(2, config['fabric_settings']['org_count'] + 1):
        enum_MSPmembers = enum_MSPmembers + f",\"'Org{org}MSP.member'\""
    enum_MSPmembers = enum_MSPmembers + ")"

    endorsement = config['fabric_settings']['endorsement_policy'] + enum_MSPmembers

    os.system(f"sed -i -e 's/substitute_enum_peers/{enum_peers}/g' {config['exp_dir']}/setup/script.sh")
    os.system(f"sed -i -e 's/substitute_enum_orgs/{enum_orgs}/g' {config['exp_dir']}/setup/script.sh")
    os.system(f"sed -i -e 's/substitute_endorsement/{endorsement}/g' {config['exp_dir']}/setup/script.sh")
    os.system(f"sed -i -e 's#substitute_tls#{string_tls}#g' {config['exp_dir']}/setup/script.sh")


def start_docker_containers(config, logger, ssh_clients, scp_clients):

    my_net = "my-net"

    # starting orderer
    # logger.info(f"Starting orderers")
    if config['fabric_settings']['orderer_type'].upper() == "KAFKA":

        # Starting zookeeper nodes
        logger.info(f"Starting zookeeper nodes")
        for zookeeper, index in enumerate(config['zookeeper_indices']):
            string_zookeeper_base = ""
            string_zookeeper_base = string_zookeeper_base + f" --network='{my_net}' --name zookeeper{zookeeper}"
            string_zookeeper_base = string_zookeeper_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"
            string_zookeeper_base = string_zookeeper_base + f" -e ZOO_MY_ID={zookeeper + 1}"
            string_zookeeper_base = string_zookeeper_base + f" -e ZOO_LOG4J_ROOT_LOGLEVEL=DEBUG"

            string_zookeeper_servers = ""
            for zookeeper1, index1 in enumerate(config['zookeeper_indices']):
                if string_zookeeper_servers != "":
                    string_zookeeper_servers = string_zookeeper_servers + " "
                string_zookeeper_servers = string_zookeeper_servers + f"server.{zookeeper1 + 1}=zookeeper{zookeeper1}:2888:3888"
            string_zookeeper_servers = f" -e ZOO_SERVERS=\"{string_zookeeper_servers}\""

            logger.debug(f" - Starting zookeeper{zookeeper} on {config['ips'][index]}")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_zookeeper_base + string_zookeeper_servers + f" hyperledger/fabric-zookeeper &> /home/ubuntu/zookeeper{zookeeper}.log)")
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"echo '(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_zookeeper_base + string_zookeeper_servers + f" hyperledger/fabric-zookeeper &> /home/ubuntu/zookeeper{zookeeper}.log)' >> /home/ubuntu/starting_command.log")
            stdout.readlines()
            # logger.debug(stdout.readlines())
            # logger.debug(stderr.readlines())

        # TODO look for log line which is needed for ready zookeepers
        time.sleep(10)

        # Starting kafka nodes
        logger.info(f"Starting kafka nodes")
        for kafka, index in enumerate(config['kafka_indices']):
            string_kafka_base = ""
            string_kafka_base = string_kafka_base + f" --network='{my_net}' --name kafka{kafka} -p 9092"
            string_kafka_base = string_kafka_base + f" -e KAFKA_MESSAGE_MAX_BYTES={config['fabric_settings']['absolute_max_bytes'] * 1024 * 1024}"
            string_kafka_base = string_kafka_base + f" -e KAFKA_REPLICA_FETCH_MAX_BYTES={config['fabric_settings']['absolute_max_bytes'] * 1024 * 1024}"
            string_kafka_base = string_kafka_base + f" -e KAFKA_UNCLEAN_LEADER_ELECTION_ENABLE=false"
            string_kafka_base = string_kafka_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"
            string_kafka_base = string_kafka_base + f" -e KAFKA_BROKER_ID={kafka}"
            string_kafka_base = string_kafka_base + f" -e KAFKA_MIN_INSYNC_REPLICAS=2"
            string_kafka_base = string_kafka_base + f" -e KAFKA_DEFAULT_REPLICATION_FACTOR=3"
            string_kafka_base = string_kafka_base + f" -e KAFKA_TOOLS_LOG4J_LOGLEVEL=DEBUG"
            string_kafka_base = string_kafka_base + f" -e KAFKA_LOG4J_ROOT_LOGLEVEL=DEBUG"

            string_kafka_zookeeper = ""
            string_kafka_zookeeper = string_kafka_zookeeper + f" -e KAFKA_ZOOKEEPER_CONNECTION_TIMEOUT_MS=360000"
            string_kafka_zookeeper = string_kafka_zookeeper + f" -e KAFKA_ZOOKEEPER_SESSION_TIMEOUT_MS=360000"

            string_kafka_zookeeper_connect = ""
            for zookeeper, _ in enumerate(config['zookeeper_indices']):
                if string_kafka_zookeeper_connect != "":
                    string_kafka_zookeeper_connect = string_kafka_zookeeper_connect + ","
                string_kafka_zookeeper_connect = string_kafka_zookeeper_connect + f"zookeeper{zookeeper}:2181"

            string_kafka_zookeeper = string_kafka_zookeeper + f" -e KAFKA_ZOOKEEPER_CONNECT={string_kafka_zookeeper_connect}"

            string_kafka_v = ""

            logger.debug(f" - Starting kafka{kafka} on {config['ips'][index]}")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_kafka_base + string_kafka_zookeeper + string_kafka_v + f" hyperledger/fabric-kafka &> /home/ubuntu/kafka{kafka}.log)")
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"echo '(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_kafka_base + string_kafka_zookeeper + string_kafka_v + f" hyperledger/fabric-kafka &> /home/ubuntu/kafka{kafka}.log)' >> /home/ubuntu/starting_command.log")
            stdout.readlines()

        time.sleep(10)

    # Starting Certificate Authorities
    """
    peer_orgs_secret_keys = []
    logger.info(f"Starting Certificate Authorities")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        # get the names of the secret keys for each peer Organizations
        stdin, stdout, stderr = ssh_clients[org - 1].exec_command(
            f"ls -a /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/peerOrganizations/org{org}.example.com/ca")
        out = stdout.readlines()
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))
        peer_orgs_secret_keys.append("".join(out).replace(f"ca.org{org}.example.com-cert.pem", "").replace("\n", "").replace(" ", "").replace("...", ""))

        # set up configurations of Certificate Authorities like with docker compose
        string_ca_base = f" --network={my_net} --name ca.org{org}.example.com -p 7054:7054"
        string_ca_base = string_ca_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"
        string_ca_base = string_ca_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"

        string_ca_ca = ""
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_HOME=/etc/hyperledger/fabric-ca-server"
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_SERVER_CA_NAME=ca.org{org}.example.com"
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_SERVER_CA_CERTFILE=/etc/hyperledger/fabric-ca-server-config/ca.org{org}.example.com-cert.pem"
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_SERVER_CA_KEYFILE=/etc/hyperledger/fabric-ca-server-config/{peer_orgs_secret_keys[org - 1]}"

        string_ca_tls = ""
        if config['fabric_settings']['tls_enabled'] == 1:
            # logger.debug("    --> TLS environment variables set")
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_ENABLED=true"
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_CERTFILE=/etc/hyperledger/fabric-ca-server-config/ca.org{org}.example.com-cert.pem"
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_KEYFILE=/etc/hyperledger/fabric-ca-server-config/{peer_orgs_secret_keys[org - 1]}"
        # else:
        #     string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_ENABLED=false"

        string_ca_v = ""
        string_ca_v = string_ca_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/ca/:/etc/hyperledger/fabric-ca-server-config"

        # Starting the Certificate Authority
        # logger.debug(f" - Starting ca for org{org} on {config['ips'][org - 1]}")
        # channel = ssh_clients[org - 1].get_transport().open_session()
        # channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_ca_base + string_ca_ca + string_ca_tls + string_ca_v + f" hyperledger/fabric-ca sh -c 'fabric-ca-server start -b admin:adminpw -d' &> /home/ubuntu/ca.org{org}.log)")
        # ssh_clients[org - 1].exec_command(f"echo \"docker run -it --rm" + string_ca_base + string_ca_ca + string_ca_tls + string_ca_v + " hyperledger/fabric-tools /bin/bash\" >> cli.sh")
    """

    logger.info("Starting orderer nodes")
    for orderer, index in enumerate(config['orderer_indices']):
        orderer = orderer + 1
        # set up configurations of orderers like with docker compose
        string_orderer_base = ""
        string_orderer_base = string_orderer_base + f" --network={my_net} --name orderer{orderer}.example.com -p 7050:7050"
        string_orderer_base = string_orderer_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"
        string_orderer_base = string_orderer_base + f" -e ORDERER_HOME=/var/hyperledger/orderer"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENADDRESS=0.0.0.0"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENPORT=7050"
        string_orderer_base = string_orderer_base + f" -e ORDERER_HOST=orderer{orderer}.example.com"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_GENESISMETHOD=file"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_GENESISFILE=/var/hyperledger/orderer/genesis.block"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LOCALMSPID=OrdererMSP"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LOCALMSPDIR=/var/hyperledger/orderer/msp"
        string_orderer_base = string_orderer_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

        string_orderer_link = ""
        for orderer2 in range(1, orderer):
            string_orderer_link = string_orderer_link + f" --link orderer{orderer2}.example.com:orderer{orderer2}.example.com"

        string_orderer_tls = ""
        if config['fabric_settings']['tls_enabled'] == 1:
            # logger.debug("    --> TLS environment variables set")
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ENABLED=true"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_PRIVATEKEY=/var/hyperledger/orderer/tls/server.key"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_CERTIFICATE=/var/hyperledger/orderer/tls/server.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ROOTCAS=[/var/hyperledger/orderer/tls/ca.crt]"

            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTAUTHREQUIRED=false"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTROOTCAS_FILES=/var/hyperledger/users/Admin@example.com/tls/ca.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTCERT_FILE=/var/hyperledger/users/Admin@example.com/tls/client.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTKEY_FILE=/var/hyperledger/users/Admin@example.com/tls/client.key"
        else:
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ENABLED=false"

        if config['fabric_settings']['orderer_type'].upper() == "RAFT":
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE=/var/hyperledger/orderer/tls/server.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY=/var/hyperledger/orderer/tls/server.key"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_ROOTCAS=[/var/hyperledger/orderer/tls/ca.crt]"

        # string_orderer_tls = string_orderer_tls + f" -e GRPC_TRACE=all" + f" -e GRPC_VERBOSITY=debug"

        string_orderer_kafka = ""
        if config['fabric_settings']['orderer_type'].upper() == "KAFKA":
            string_orderer_kafka = string_orderer_kafka + " -e ORDERER_KAFKA_BROKERS=["
            for kafka, _ in enumerate(config['kafka_indices']):
                if string_orderer_kafka != " -e ORDERER_KAFKA_BROKERS=[":
                    string_orderer_kafka = string_orderer_kafka + ","
                string_orderer_kafka = string_orderer_kafka + f"kafka{kafka}:9092"
            string_orderer_kafka = string_orderer_kafka + "]"
            string_orderer_kafka = string_orderer_kafka + f" -e ORDERER_KAFKA_RETRY_SHORTINTERVAL=1s"
            string_orderer_kafka = string_orderer_kafka + f" -e ORDERER_KAFKA_RETRY_SHORTTOTAL=30s"
            string_orderer_kafka = string_orderer_kafka + f" -e ORDERER_KAFKA_VERBOSE=true"

        string_orderer_v = ""
        string_orderer_v = string_orderer_v + f" -v $(pwd)/channel-artifacts/genesis.block:/var/hyperledger/orderer/genesis.block"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/msp:/var/hyperledger/orderer/msp"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls:/var/hyperledger/orderer/tls"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/users:/var/hyperledger/users"
        string_orderer_v = string_orderer_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric"

        # Starting the orderers
        logger.debug(f" - Starting orderer{orderer} on {config['ips'][index]}")
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_orderer_base + string_orderer_kafka + string_orderer_tls + string_orderer_v + f" hyperledger/fabric-orderer orderer &> /home/ubuntu/orderer{orderer}.log)")
        ssh_clients[index].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_orderer_base + string_orderer_kafka + string_orderer_tls + string_orderer_v + " hyperledger/fabric-tools /bin/bash\" >> /data/cli.sh)")

    # starting peers and databases
    logger.info(f"Starting databases and peers")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        for peer in range(0, config['fabric_settings']['peer_count']):
            index = config['peer_indices'][(org-1) * config['fabric_settings']['peer_count'] + peer]
            ip = config['ips'][index]

            if config['fabric_settings']['database'] == "CouchDB":
                # set up CouchDB configuration
                string_database_base = ""
                string_database_base = string_database_base + f" --network='{my_net}' --name couchdb{peer}.org{org} -p 5984:5984"
                string_database_base = string_database_base + f" -e COUCHDB_USER= -e COUCHDB_PASSWORD="
                string_database_base = string_database_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

                # Starting the CouchDBs
                logger.debug(f" - Starting database couchdb{peer}.org{org} on {ip}")
                channel = ssh_clients[index].get_transport().open_session()
                channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_database_base + f" hyperledger/fabric-couchdb &> /home/ubuntu/couchdb{peer}.org{org}.log)")

            # Setting up configuration of peer like with docker compose
            string_peer_base = ""
            string_peer_base = string_peer_base + f" --network='{my_net}' --name peer{peer}.org{org}.example.com -p 7051:7051 -p 7053:7053"

            string_peer_link = ""
            for orderer2 in range(1, config['fabric_settings']['orderer_count'] + 1):
                string_peer_link = string_peer_link + f" --link orderer{orderer2}.example.com:orderer{orderer2}.example.com"

            for org2 in range(1, org + 1):
                if org2 < org:
                    end = config['fabric_settings']['peer_count']
                else:
                    end = peer

                for peer2 in range(0, end):
                    string_peer_link = string_peer_link + f" --link peer{peer2}.org{org2}.example.com:peer{peer2}.org{org2}.example.com"

            string_peer_database = ""
            if config['fabric_settings']['database'] == "CouchDB":
                string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_STATEDATABASE=CouchDB"
                string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_COUCHDBADDRESS=couchdb{peer}.org{org}:5984"
                string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_USERNAME="
                string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_PASSWORD="

            string_peer_core = ""
            string_peer_core = string_peer_core + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"
            # string_peer_core = string_peer_core + f" -e CORE_LOGGING_MSP={config['fabric_settings']['log_level']}"
            string_peer_core = string_peer_core + f" -e CORE_PEER_ADDRESS=peer{peer}.org{org}.example.com:7051"
            string_peer_core = string_peer_core + f" -e CORE_PEER_ADDRESSAUTODETECT=false"
            string_peer_core = string_peer_core + f" -e CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock"
            string_peer_core = string_peer_core + f" -e CORE_PEER_NETWORKID={my_net}"
            # string_peer_core = string_peer_core + f" -e CORE_NEXT=true"
            # string_peer_core = string_peer_core + f" -e CORE_PEER_ENDORSER_ENABLED=true"
            string_peer_core = string_peer_core + f" -e CORE_PEER_ID=peer{peer}.org{org}.example.com"
            string_peer_core = string_peer_core + f" -e CORE_PEER_PROFILE_ENABLED=true"
            # string_peer_core = string_peer_core + f" -e CORE_PEER_COMMITTER_LEDGER_ORDERER=orderer1.example.com:7050"
            # string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_IGNORESECURITY=true"
            string_peer_core = string_peer_core + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"
            string_peer_core = string_peer_core + f" -e CORE_PEER_LOCALMSPID=Org{org}MSP"
            string_peer_core = string_peer_core + f" -e CORE_PEER_MSPCONFIGPATH=/var/hyperledger/fabric/msp"
            string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_EXTERNALENDPOINT=peer{peer}.org{org}.example.com:7051"
            # string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_USELEADERELECTION=false"
            # string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_ORGLEADER=true"
            # if peer != 0:
            #     string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_BOOTSTRAP=peer0.org{org}.example.com:7051"

            string_peer_core = string_peer_core + f" -e CORE_PEER_CHAINCODELISTENADDRESS=peer{peer}.org{org}.example.com:7052"

            string_peer_tls = ""
            if config['fabric_settings']['tls_enabled'] == 1:
                # logger.debug("    --> TLS environment variables set")
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ENABLED=true"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_CLIENTAUTHREQUIRED=false"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_CERT_FILE=/var/hyperledger/fabric/tls/server.crt"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_KEY_FILE=/var/hyperledger/fabric/tls/server.key"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/fabric/tls/ca.crt"
            else:
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ENABLED=false"

            string_peer_tls = string_peer_tls + f" -e GRPC_TRACE=all" + f" -e GRPC_VERBOSITY=debug"

            string_peer_v = ""
            string_peer_v = string_peer_v + f" -v /var/run/:/host/var/run/"
            string_peer_v = string_peer_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/msp:/var/hyperledger/fabric/msp"
            string_peer_v = string_peer_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls:/var/hyperledger/fabric/tls"
            string_peer_v = string_peer_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

            # Starting the peers
            logger.debug(f" - Starting peer{peer}.org{org} on {ip}")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_peer_base + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + f" hyperledger/fabric-peer peer node start &> /home/ubuntu/peer{peer}.org{org}.log)")
            ssh_clients[index].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_peer_base + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + " hyperledger/fabric-tools /bin/bash\" >> /data/cli.sh)")

    # Waiting for a few seconds until all peers and orderers have started

    time.sleep(10)

    index_last_node = config['peer_indices'][-1]
    # Creating script and pushing it to the last node
    logger.debug(f"Executing script on {config['ips'][index_last_node]}  which creates channel, adds peers to channel, installs and instantiates all chaincode - can take some minutes")
    write_script(config, logger)
    stdin, stdout, stderr = ssh_clients[index_last_node].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")
    stdout.readlines()
    # logger.debug(stdout.readlines())
    # logger.debug(stdout.readlines())
    scp_clients[index_last_node].put(f"{config['exp_dir']}/setup/script.sh", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")

    # Setting up configuration of cli like with docker compose
    string_cli_base = ""
    string_cli_base = string_cli_base + f" --network='{my_net}' --name cli -p 12051:7051 -p 12053:7053"
    string_cli_base = string_cli_base + f" -e GOPATH=/opt/gopath"
    string_cli_base = string_cli_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"

    string_cli_link = ""
    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        string_cli_link = string_cli_link + f" --link orderer{orderer}.example.com:orderer{orderer}.example.com"

    for org in range(1, org + 1):
        for peer in range(0, config['fabric_settings']['peer_count'] + 1):
            string_cli_link = string_cli_link + f" --link peer{peer}.org{org}.example.com:peer{peer}.org{org}.example.com"

    string_cli_core = ""
    string_cli_core = string_cli_core + f" -e CORE_PEER_LOCALMSPID=Org{org}MSP"
    string_cli_core = string_cli_core + f" -e CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock"
    string_cli_core = string_cli_core + f" -e CORE_PEER_ID=cli"
    string_cli_core = string_cli_core + f" -e CORE_PEER_ADDRESS=peer0.org{org}.example.com:7051"
    string_cli_core = string_cli_core + f" -e CORE_PEER_NETWORKID={my_net}"
    string_cli_core = string_cli_core + f" -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/users/Admin@org{org}.example.com/msp"
    string_cli_core = string_cli_core + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

    string_cli_tls = ""
    if config['fabric_settings']['tls_enabled'] == 1:
        # logger.debug("    --> TLS environment variables set")
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ENABLED=true"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_CERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/server.crt"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_KEY_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/server.key"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/ca.crt"
    else:
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ENABLED=false"

    string_cli_v = ""
    string_cli_v = string_cli_v + f" -v /var/run/:/host/var/run/"
    string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode/:/opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/"
    string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config:/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/"
    string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts:/opt/gopath/src/github.com/hyperledger/fabric/peer/scripts/"
    string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts:/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts"
    string_cli_v = string_cli_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

    # execute script.sh on last node
    stdin, stdout, stderr = ssh_clients[index_last_node].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_cli_base + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash -c '(ls -la && cd scripts && ls -la && chmod 777 script.sh && ls -la && cd .. && ./scripts/script.sh)' |& tee /home/ubuntu/setup.log)")
    out = stdout.readlines()

    # save the cli command on the last node and save it in exp_dir
    ssh_clients[index_last_node].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_cli_base + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash\" >> /data/cli2.sh)")

    if out[len(out) - 1] == "========= All GOOD, BMHN execution completed =========== \n":
        logger.info("")
        logger.info("**************** !!! Fabric network formation was successful !!! *********************")
        logger.info("")
    else:
        logger.info("")
        logger.info("******************!!! ERROR: Fabric network formation failed !!! *********************")
        for index, _ in enumerate(out):
            logger.debug(out[index].replace("\n", ""))

        raise Exception("Blockchain did not start properly - Omitting or repeating")


def fabric_restart(config, logger, ssh_clients, scp_clients):
    try:
        fabric_shutdown(config, logger, ssh_clients, scp_clients)
        start_docker_containers(config, logger, ssh_clients, scp_clients)
    except Exception as e:
        logger.exception(e)
        fabric_shutdown(config, logger, ssh_clients, scp_clients)
        start_docker_containers(config, logger, ssh_clients, scp_clients)

def push_stuff(config, ssh_clients, scp_clients, indices_sources, indices_targets, logger):

    logger.debug(f"Sources: {indices_sources}, targets: {indices_targets}")

    jobs = []
    for index, index_source in enumerate(indices_sources):
        # logger.debug(f"Creating thread {index} for pushing from {index_source} to {indices_targets[index]}")
        thread = threading.Thread(target=push_stuff_single(config, ssh_clients, scp_clients, index_source, indices_targets[index], logger))
        # logger.debug(f"Starting thread {index}")
        thread.start()
        jobs.append(thread)

    for j in jobs:
        # logger.debug(f"Joining thread {j}")
        j.join()


def push_stuff_single(config, ssh_clients, scp_clients, index_source, index_target, logger):

    # logger.debug(f"Starting to push to index {index_target}")
    # deleting data at the vm associated with source_index and copying it to the vm associated with the target index
    # use scp -v for verbose mode
    stdin, stdout, stderr = ssh_clients[index_source].exec_command(f"ssh -o 'StrictHostKeyChecking no' -i /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem ubuntu@{config['priv_ips'][index_target]} 'sudo rm -rf /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts && echo Success'")
    wait_and_log(stdout, stderr)
    stdin, stdout, stderr = ssh_clients[index_source].exec_command(f"scp -o 'StrictHostKeyChecking no' -ri /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config ubuntu@{config['priv_ips'][index_target]}:/data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo Success")
    wait_and_log(stdout, stderr)
    stdin, stdout, stderr = ssh_clients[index_source].exec_command(f"scp -o 'StrictHostKeyChecking no' -ri /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts ubuntu@{config['priv_ips'][index_target]}:/data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo Success")
    wait_and_log(stdout, stderr)
    stdin, stdout, stderr = ssh_clients[index_source].exec_command(f"scp -o 'StrictHostKeyChecking no' -ri /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode ubuntu@{config['priv_ips'][index_target]}:/data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo Success")
    wait_and_log(stdout, stderr)
    # logger.debug(f"Successfully pushed to index {index_target}")



