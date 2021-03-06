#  Copyright 2021 ChainLab
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


import datetime
import json
import os
import sys
import threading

from BlockchainFormation.utils.utils import *


class Fabric_Network:

    @staticmethod
    def check_config(config, logger):

        try:
            internal_orderer = config['fabric_settings']['internal_orderer']
        except Exception as e:
            internal_orderer = 0

        try:
            external_database = config['fabric_settings']['external_database']
        except Exception as e:
            try:
                external_database = config['fabric_settings']['external']
            except Exception as e:
                logger.exception(e)

        logger.debug(f"Checking the fabric config")
        if config['fabric_settings']['orderer_type'].upper() == "KAFKA":
            count = config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count'] \
                    + config['fabric_settings']['orderer_count'] + config['fabric_settings']['zookeeper_count'] \
                    + config['fabric_settings']['kafka_count']
        elif config['fabric_settings']['orderer_type'].upper() == "RAFT":
            count = config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count'] + config['fabric_settings']['orderer_count']
        elif config['fabric_settings']['orderer_type'].upper() == "SOLO":
            count = config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count'] + 1
            if config['fabric_settings']['orderer_count'] != 1:
                logger.info(f"It seems that orderer_count is different from the expected number of orderers for orderer type 'solo'")
                logger.info(f"Setting orderer_count to 1")
                config['fabric_settings']['orderer_count'] = 1
        else:
            raise Exception("No valid orderer type")

        # if the CouchDB is separate, double the number of vms required for the peers
        # if config['fabric_settings']['database'] == "CouchDB" and config['fabric_settings']['external_database'] == 1:
        if config['fabric_settings']['database'] == "CouchDB" and external_database == 1:
            count = count + config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count']

        # if the Orderers are not separate, decrease the number of vms required for the peers
        # if config['fabric_settings']['internal_orderer'] == 1:
        if internal_orderer == 1:
            if config['fabric_settings']['orderer_type'] != "solo" and config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count'] < config['fabric_settings']['orderer_count']:
                raise Exception("There are more orderers than peers - cannot make the orderers internal")
            else:
                if config['fabric_settings']['orderer_type'] == "solo":
                    count = count - 1
                else:
                    count = count - config['fabric_settings']['orderer_count']

        if count != config['vm_count']:
            logger.info(f"It seems that vm_count ({config['vm_count']}) is different from the expected number of necessary nodes ({count})")
            logger.info(f"Setting vm_count to {count}")
            config['vm_count'] = count

    @staticmethod
    def shutdown(node_handler):
        """
        runs the fabric specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        logger.info("Getting logs from vms")
        time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        os.mkdir(f"{config['exp_dir']}/fabric_logs_{time}")
        for index, ip in enumerate(config['ips']):
            scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")
            try:
                scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs_{time}/")
                logger.info("Logs fetched successfully")
                # stdin, stdout, stderr = ssh_clients[index].exec_command("rm /home/ubuntu/*.log")
                # logger.info(stdout.readlines())
                # logger.info(stderr.readlines())
            except exception as e:
                logger.exception(e)
                logger.info(f"No logs available on {ip}")

        logger.info("")


    @staticmethod
    def startup(node_handler):

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients
        dir_name = os.path.dirname(os.path.realpath(__file__))

        try:
            internal_orderer = config['fabric_settings']['internal_orderer']
        except Exception as e:
            internal_orderer = 0

        try:
            external_database = config['fabric_settings']['external_database']
        except Exception as e:
            try:
                external_database = config['fabric_settings']['external']
            except Exception as e:
                logger.exception(e)

        # the indices of the different roles
        config['orderer_indices'] = list(range(0, config['fabric_settings']['orderer_count']))

        # if config['fabric_settings']['internal_orderer'] == 1:
        if internal_orderer == 1:
            start_index = 0
        else:
            start_index = config['fabric_settings']['orderer_count']

        # if config['fabric_settings']['database'] == "CouchDB" and config['fabric_settings']['external_database'] == 1:
        if config['fabric_settings']['database'] == "CouchDB" and external_database == 1:

            config['peer_indices'] = list(range(start_index, start_index + config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count']))
            config['db_indices'] = list(range(start_index + config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count'], start_index + 2 * config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count']))

            if config['fabric_settings']['orderer_type'].upper() == "KAFKA":
                config['zookeeper_indices'] = list(range(start_index + 2 * config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'],
                                                         start_index + 2 * config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count']))
                config['kafka_indices'] = list(range(start_index + 2 * config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'],
                                                     start_index + 2 * config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'] + config['fabric_settings']['kafka_count']))
            else:
                config['zookeeper_indices'] = []
                config['kafka_indices'] = []


        else:
            config['peer_indices'] = list(range(start_index, start_index + config['fabric_settings']['org_count'] * config['fabric_settings']['peer_count']))
            config['db_indices'] = config['peer_indices']

            if config['fabric_settings']['orderer_type'].upper() == "KAFKA":
                config['zookeeper_indices'] = list(range(start_index + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'],
                                                         start_index + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count']))
                config['kafka_indices'] = list(range(start_index + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'],
                                                     start_index + config['fabric_settings']['peer_count'] * config['fabric_settings']['org_count'] + config['fabric_settings']['zookeeper_count'] + config['fabric_settings']['kafka_count']))
            else:
                config['zookeeper_indices'] = []
                config['kafka_indices'] = []

        logger.info(f"Orderer indices: {config['orderer_indices']}")
        logger.info(f"Peer indices: {config['peer_indices']}")

        # Putting the nodes in groups
        # currently only reasonable for raft
        config['groups'] = []
        for org in range(0, config['fabric_settings']['org_count']):

            # peer_range = range(org * config['fabric_settings']['peer_count'], (org + 1) * (config['fabric_settings']['peer_count']))
            peer_range = list(org + np.array(range(0, config['fabric_settings']['peer_count'])) * config['fabric_settings']['org_count'])

            peer_indices = []
            peer_ips = []

            db_indices = []
            db_ips = []

            for _, node in enumerate(peer_range):
                peer_indices.append(config['peer_indices'][node])
                peer_ips.append(config['priv_ips'][config['peer_indices'][node]])

                # if config['fabric_settings']['database'] == "CouchDB" and config['fabric_settings']['external_database'] == 1:
                if config['fabric_settings']['database'] == "CouchDB" and external_database == 1:
                    db_indices.append(config['db_indices'][node])
                    db_ips.append(config['priv_ips'][config['db_indices'][node]])

            if config['fabric_settings']['orderer_count'] % config['fabric_settings']['org_count'] == 0:

                n = int(config['fabric_settings']['orderer_count'] / config['fabric_settings']['org_count'])

                orderer_indices = []
                orderer_ips = []

                for orderer in range(org * n, (org + 1) * n):
                    orderer_indices.append(config['orderer_indices'][orderer])
                    orderer_ips.append(config['priv_ips'][config['orderer_indices'][orderer]])

            else:

                orderer_indices = []
                orderer_ips = []

            group_indices = unique(peer_indices + db_indices + orderer_indices)

            config['groups'].append(group_indices)

        # all the other nodes are a single group
        all_indices = range(0, len(config['ips']))
        all_group_members = [i for j in config['groups'] for i in j]

        for index in all_indices:
            if index not in all_group_members:
                config['groups'].append([index])

        logger.info(f"Groups: {config['groups']}")


        # the indices of the blockchain nodes
        config['node_indices'] = config['peer_indices']

        # create directories for the fabric logs and all the setup data (crypto-stuff, config files and scripts which are exchanged with the VMs)
        os.mkdir(f"{config['exp_dir']}/fabric_logs")
        os.mkdir(f"{config['exp_dir']}/api")

        # Creating docker swarm
        logger.info("Preparing & starting docker swarm")

        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo docker swarm init --advertise-addr {config['priv_ips'][0]}")
        out = stdout.readlines()
        for index, _ in enumerate(out):
            logger.debug(out[index].replace("\n", ""))

        # logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm join-token manager")
        out = stdout.readlines()
        logger.debug(out)
        logger.debug("".join(stderr.readlines()))
        join_command = out[2].replace("    ", "").replace("\n", "")

        for index, _ in enumerate(config['priv_ips']):

            if index != 0:
                stdin, stdout, stderr = ssh_clients[index].exec_command("sudo " + join_command + f" --advertise-addr {config['priv_ips'][index]}")
                out = stdout.readlines()
                logger.debug(out)
                logger.debug("".join(stderr.readlines()))

        config['join_command'] = "sudo " + join_command

        # Name of the swarm network
        my_net = "my-net"
        # stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo docker network create --subnet 10.10.0.0/16 --attachable --driver overlay {my_net}")
        stdin, stdout, stderr = ssh_clients[0].exec_command(
            f"sudo docker network create --attachable --driver overlay {my_net}")
        out = stdout.readlines()
        logger.debug(out)
        logger.debug("".join(stderr.readlines()))
        network = out[0].replace("\n", "")

        logger.info("Testing whether setup was successful")
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command("sudo docker node ls")
            out = stdout.readlines()
            # for index2, _ in enumerate(out):
                # logger.debug(out[index2].replace("\n", ""))

            # logger.debug("".join(stderr.readlines()))
            if len(out) == len(config['priv_ips']) + 1:
                logger.info(f"Docker swarm started successfully on node{index}")
            else:
                logger.info("Docker swarm setup was not successful")
                logger.info(f"Docker swarm setup not successful on {config['pub_ips'][index]}")


        logger.info(f"Creating crypto-config.yaml and pushing it to {config['ips'][0]}")
        Fabric_Network.write_crypto_config(config, logger)

        stdin, stdout, stderr = ssh_clients[0].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config.yaml")
        stdout.readlines()
        wait_and_log(stdout, stderr)

        scp_clients[0].put(f"{config['exp_dir']}/setup/crypto-config.yaml", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config.yaml")

        logger.info(f"Creating configtx and pushing it to {config['ips'][0]}")
        Fabric_Network.write_configtx(config, logger)

        stdin, stdout, stderr = ssh_clients[0].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/configtx.yaml")
        wait_and_log(stdout, stderr)

        scp_clients[0].put(f"{config['exp_dir']}/setup/configtx.yaml", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/configtx.yaml")

        logger.info(f"Creating bmhn.sh and pushing it to {config['ips'][0]}")
        os.system(f"cp {dir_name}/setup/bmhn_raw.sh {config['exp_dir']}/setup/bmhn.sh")
        enum_orgs = "1"
        for org in range(2, config['fabric_settings']['org_count'] + 1):
            enum_orgs = enum_orgs + f" {org}"

        enum_channels = '('
        for channel in range(1, config['fabric_settings']['channel_count'] + 1):
            if channel != 1:
                enum_channels = enum_channels + ' '

            enum_channels = enum_channels + f"mychannel{channel}"

        enum_channels = enum_channels + ')'

        os.system(f"sed -i -e 's/substitute_enum_orgs/{enum_orgs}/g' {config['exp_dir']}/setup/bmhn.sh")
        os.system(f"sed -i -e 's/substitute_enum_channels/{enum_channels}/g' {config['exp_dir']}/setup/bmhn.sh")
        # os.system(f"sed -i -e 's/substitute_enum_batch_timeouts/('0.5 0.5 0.3')/g' {config['exp_dir']}/setup/bmhn.sh")
        stdin, stdout, stderr = ssh_clients[0].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/bmhn.sh")
        stdout.readlines()
        wait_and_log(stdout, stderr)

        scp_clients[0].put(f"{config['exp_dir']}/setup/bmhn.sh", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/bmhn.sh")

        logger.info(f"Creating crypto-stuff on {config['ips'][0]} by executing bmhn.sh")
        stdin, stdout, stderr = ssh_clients[0].exec_command("rm -rf /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config")
        wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[0].exec_command("( cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo y | bash ./bmhn.sh )")
        out = stdout.readlines()
        for index, _ in enumerate(out):
            logger.debug(out[index].replace("\n", ""))

        logger.debug("".join(stderr.readlines()))

        logger.info(f"Getting crypto-config and channel-artifacts from {config['ips'][0]}...")
        scp_clients[0].get("/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config", f"{config['exp_dir']}/setup", recursive=True)
        scp_clients[0].get("/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts", f"{config['exp_dir']}/setup", recursive=True)

        logger.info("Pushing crypto-config, channel-artifacts, and chaincode to all remaining other nodes")
        indices = unique(config['orderer_indices'] + config['peer_indices'])
        logger.info(f"Indices: {indices}")

        # pushing the ssh-key and the chaincode on the first vm
        scp_clients[0].put(f"{config['priv_key_path']}", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem")
        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo chmod 600 /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())
        scp_clients[0].put(f"{dir_name}/chaincode/benchcontract", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode", recursive=True)
        Fabric_Network.write_collections(config, logger)
        scp_clients[0].put(f"{config['exp_dir']}/setup/collections.json", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode/benchcontract")
        logger.debug("Successfully pushed to index 0.")

        finished_indices = [indices[0]]
        remaining_indices = indices[1:len(indices)]
        while remaining_indices != []:
            n_targets = min(len(finished_indices), len(remaining_indices))
            indices_sources = finished_indices[0:n_targets]
            indices_targets = remaining_indices[0:n_targets]

            Fabric_Network.push_stuff(config, ssh_clients, scp_clients, indices_sources, indices_targets, logger)

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

        Fabric_Network.start_docker_containers(config, logger, ssh_clients, scp_clients)

        Fabric_Network.setup_network(config, ssh_clients, scp_clients, logger, "network_setup")

        # leader_index = Fabric_Network.find_leader(config, ssh_clients, scp_clients, logger)
        # index = Fabric_Network.shutdown_raft_leader(config, ssh_clients, scp_clients, logger)
        # Fabric_Network.find_leader(config, ssh_clients, scp_clients, logger)
        # Fabric_Network.restart_orderer(config, ssh_clients, scp_clients, logger, leader_index)

        # Fabric_Network.stopstart_leader(node_handler)
        # Fabric_Network.find_leader(config, ssh_clients, scp_clients, logger)


    @staticmethod
    def write_crypto_config(config, logger):
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

    @staticmethod
    def write_configtx(config, logger):
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
                logger.info("RAFT is only supported with TLS enabled")
                raise Exception("RAFT is only supported with TLS enabled")

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
                f.write(f"            - kafka{orderer - 1}:9092\n")

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

    @staticmethod
    def write_collections(config, logger):
        with open(f"{config['exp_dir']}/setup/collections.json", "w+") as file:

            if config['fabric_settings']['private_fors'] == "all":
                n = config['fabric_settings']['org_count']
            else:
                n = config['fabric_settings']['private_fors']

            collections = []

            for org in range(1, config['fabric_settings']['org_count'] + 1):
                collection = {}

                policy = "OR("

                for index in range(n):
                    if index != 0:
                        policy = policy + ","

                    policy = policy + f"'Org{((org + index) % config['fabric_settings']['org_count']) + 1}MSP.member'"

                policy = policy + ")"

                collection['name'] = f"Collection{org}"
                collection['policy'] = policy
                collection['requiredPeerCount'] = 1
                collection['maxPeerCount'] = config['fabric_settings']['peer_count']
                collection['blockToLive'] = 1000000
                collection['memberOnlyRead'] = True

                collections.append(collection)

            json.dump(collections, file, default=datetimeconverter, indent=4)

    @staticmethod
    def write_script(config, logger, name, number_of_endorsers=None):
        dir_name = os.path.dirname(os.path.realpath(__file__))
        os.system(f"cp {dir_name}/setup/script_raw_1.sh {config['exp_dir']}/setup/{name}.sh")

        f = open(f"{config['exp_dir']}/setup/{name}.sh", "a")

        f.write("\n\nsetGlobals() {\n\n")
        f.write("    CORE_PEER_ADDRESS=peer$1.org$2.example.com:7051\n")
        f.write("    CORE_PEER_LOCALMSPID=Org$2MSP\n")

        f.write("    CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/ca.crt\n")
        f.write("    CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/users/Admin@org$2.example.com/msp\n")

        if config['fabric_settings']['tls_enabled']:
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

        if name == "network_setup":

            os.system(f"cat {dir_name}/setup/script_raw_3.sh >> {config['exp_dir']}/setup/{name}.sh")

        elif name == "chaincode_installation":

            os.system(f"cat {dir_name}/setup/script_raw_2.sh >> {config['exp_dir']}/setup/{name}.sh")

        else:
            logger.info("Invalid operation")
            raise Exception("Invalid operation")

        if config['fabric_settings']['tls_enabled']:
            # logger.debug("    --> TLS environment variables set")
            string_tls = f"--tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem"
        else:
            string_tls = f""

        # append the parts of script to the final script

        # substitute the enumeration of peers and orgs
        enum_peers = "0"
        for peer in range(1, config['fabric_settings']['peer_count']):
            enum_peers = enum_peers + f" {peer}"

        enum_orgs = "1"
        for org in range(2, config['fabric_settings']['org_count'] + 1):
            enum_orgs = enum_orgs + f" {org}"

        if number_of_endorsers != None:
                endorsers_count = number_of_endorsers

        elif config['fabric_settings']['endorsement_policy'] == "OR":
            endorsers_count = 1

        elif config['fabric_settings']['endorsement_policy'] == "ALL":
            endorsers_count = config['fabric_settings']['org_count']

        elif config['fabric_settings']['endorsement_policy'] >= 1 and config['fabric_settings']['endorsement_policy'] <= config['fabric_settings']['org_count']:
            endorsers_count = config['fabric_settings']['endorsement_policy']

        else:
            raise Exception("Invalid endorsement policy")

        endorsement = f"OutOf ({endorsers_count}, \"'Org1MSP.member'\""
        for org in range(2, config['fabric_settings']['org_count'] + 1):
            endorsement = endorsement + f",\"'Org{org}MSP.member'\""
        endorsement = endorsement + ")"

        os.system(f"sed -i -e 's/substitute_enum_peers/{enum_peers}/g' {config['exp_dir']}/setup/{name}.sh")
        os.system(f"sed -i -e 's/substitute_enum_orgs/{enum_orgs}/g' {config['exp_dir']}/setup/{name}.sh")
        os.system(f"sed -i -e 's/substitute_keyspace/{config['fabric_settings']['keyspace_size']}/g' {config['exp_dir']}/setup/{name}.sh")
        os.system(f"sed -i -e 's/substitute_endorsement/{endorsement}/g' {config['exp_dir']}/setup/{name}.sh")
        os.system(f"sed -i -e 's#substitute_tls#{string_tls}#g' {config['exp_dir']}/setup/{name}.sh")

    @staticmethod
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
                channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run" + string_zookeeper_base + string_zookeeper_servers + f" hyperledger/fabric-zookeeper &> /home/ubuntu/zookeeper{zookeeper}.log)")
                stdin, stdout, stderr = ssh_clients[index].exec_command(
                    f"echo '(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run -it --rm" + string_zookeeper_base + string_zookeeper_servers + f" hyperledger/fabric-zookeeper &> /home/ubuntu/zookeeper{zookeeper}.log)' > /home/ubuntu/starting_command.log")
                stdout.readlines()
                # logger.debug(stdout.readlines())
                # logger.debug(stderr.readlines())

            # TODO look for log line which is needed for ready zookeepers
            time.sleep(30)

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
                channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run" + string_kafka_base + string_kafka_zookeeper + string_kafka_v + f" hyperledger/fabric-kafka &> /home/ubuntu/kafka{kafka}.log)")
                stdin, stdout, stderr = ssh_clients[index].exec_command(
                    f"echo '(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run -it --rm" + string_kafka_base + string_kafka_zookeeper + string_kafka_v + f" hyperledger/fabric-kafka &> /home/ubuntu/kafka{kafka}.log)' > /home/ubuntu/starting_command.log")
                stdout.readlines()

            time.sleep(30)

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
            if config['fabric_settings']['tls_enabled']:
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
            # ssh_clients[org - 1].exec_command(f"echo \"docker run -it --rm" + string_ca_base + string_ca_ca + string_ca_tls + string_ca_v + " hyperledger/fabric-tools /bin/bash\" > cli.sh")
        """

        logger.info("Starting orderer nodes")
        for orderer, index in enumerate(config['orderer_indices']):
            orderer = orderer + 1
            # set up configurations of orderers like with docker compose
            string_orderer_base = ""
            string_orderer_base = string_orderer_base + f" --network={my_net} --name orderer{orderer}.example.com -p 7050:7050 -p 9442:9442"
            string_orderer_base = string_orderer_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_KEEPALIVE_SERVERTIMEOUT=1000s"
            string_orderer_base = string_orderer_base + f" -e ORDERER_HOME=/var/hyperledger/orderer"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENADDRESS=0.0.0.0"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENPORT=7050"
            string_orderer_base = string_orderer_base + f" -e ORDERER_HOST=orderer{orderer}.example.com"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_GENESISMETHOD=file"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_GENESISFILE=/var/hyperledger/orderer/genesis.block"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LOCALMSPID=OrdererMSP"
            string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LOCALMSPDIR=/var/hyperledger/orderer/msp"
            string_orderer_base = string_orderer_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"
            string_orderer_base = string_orderer_base + f" -e ORDERER_OPERATIONS_LISTENADDRESS=0.0.0.0:9442"
            string_orderer_base = string_orderer_base + f" -e ORDERER_METRICS_PROVIDER=prometheus"

            string_orderer_link = ""
            for orderer2 in range(1, orderer):
                string_orderer_link = string_orderer_link + f" --link orderer{orderer2}.example.com:orderer{orderer2}.example.com"

            string_orderer_tls = ""
            if config['fabric_settings']['tls_enabled']:
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

            command = "docker run" + string_orderer_base + string_orderer_kafka + string_orderer_tls + string_orderer_v + f" hyperledger/fabric-orderer orderer > /home/ubuntu/orderer{orderer}.log 2>&1"

            channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger "
                                 f"&& echo \"{command}\" >> /home/ubuntu/start_orderer.sh "
                                 f"&& sudo chmod 775 /home/ubuntu/start_orderer.sh && bash /home/ubuntu/start_orderer.sh)")

            stdin, stdout, stderr = ssh_clients[index].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_orderer_base + string_orderer_kafka + string_orderer_tls + string_orderer_v + " hyperledger/fabric-tools /bin/bash\" > /data/cli.sh)")
            wait_and_log(stdout, stderr)

        # starting peers and databases
        logger.info(f"Starting databases and peers")
        for org in range(1, config['fabric_settings']['org_count'] + 1):
            for peer in range(0, config['fabric_settings']['peer_count']):
                index_peer = config['peer_indices'][(org - 1) * config['fabric_settings']['peer_count'] + peer]
                index_db = config['db_indices'][(org - 1) * config['fabric_settings']['peer_count'] + peer]
                ip_peer = config['ips'][index_peer]
                ip_db = config['ips'][index_db]

                if config['fabric_settings']['database'] == "CouchDB":
                    # set up CouchDB configuration
                    string_database_base = ""
                    string_database_base = string_database_base + f" --network='{my_net}' --name couchdb{peer}.org{org} -p 5984:5984"
                    string_database_base = string_database_base + f" -e COUCHDB_USER= -e COUCHDB_PASSWORD="
                    string_database_base = string_database_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

                    # Starting the CouchDBs
                    logger.debug(f" - Starting database couchdb{peer}.org{org} on {ip_db}")

                    command = f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run" + string_database_base + f" hyperledger/fabric-couchdb > /home/ubuntu/couchdb{peer}.org{org}.log 2>&1)"

                    channel = ssh_clients[index_db].get_transport().open_session()
                    channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger "
                                         f"&& echo \"{command}\" >> /home/ubuntu/start_couchdb.sh "
                                         f"&& sudo chmod 775 /home/ubuntu/start_couchdb.sh && bash /home/ubuntu/start_couchdb.sh)")

                # Setting up configuration of peer like with docker compose
                string_peer_base = ""
                string_peer_base = string_peer_base + f" --network='{my_net}' --name peer{peer}.org{org}.example.com -p 7051:7051 -p 7053:7053 -p 9443:9443"

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
                string_peer_core = string_peer_core + f" -e CORE_CHAINCODE_EXECUTETIMEOUT=1000s"
                string_peer_core = string_peer_core + f" -e CORE_PEER_KEEPALIVE_CLIENT_TIMEOUT=1000s"
                string_peer_core = string_peer_core + f" -e CORE_PEER_KEEPALIVE_DELIVERYCLIENT_TIMEOUT=1000s"
                string_peer_core = string_peer_core + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_REQUESTTIMEOUT=1000s"
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
                string_peer_core = string_peer_core + f" -e CORE_OPERATIONS_LISTENADDRESS=0.0.0.0:9443"
                string_peer_core = string_peer_core + f" -e CORE_METRICS_PROVIDER=prometheus"

                string_peer_tls = ""
                if config['fabric_settings']['tls_enabled']:
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
                logger.debug(f" - Starting peer{peer}.org{org} on {ip_peer}")
                channel = ssh_clients[index_peer].get_transport().open_session()
                command = f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run" + string_peer_base + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + f" hyperledger/fabric-peer peer node start > /home/ubuntu/peer{peer}.org{org}.log 2>&1)"
                ssh_clients[index_peer].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_peer_base + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + " hyperledger/fabric-tools /bin/bash\" > /data/cli.sh)")

                channel.exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger "
                                     f"&& echo \"{command}\" >> /home/ubuntu/start_peer.sh "
                                     f"&& sudo chmod 775 /home/ubuntu/start_peer.sh && bash /home/ubuntu/start_peer.sh)")

        retry = True
        counter = 0
        while retry and counter < 10:
            """
            if counter == 10:
                for index, _ in enumerate(config['ips']):
                    ssh_clients[index].exec_command("sudo reboot")

                logger.info("Waiting till all machines have rebooted")
                time.sleep(10)

                status_flags = wait_till_done(config, ssh_clients, config['ips'], 10 * 60, 10, "/var/log/user_data_success.log", False, 10 * 60, logger)
                if False in status_flags:
                        raise Exception(f"Instance reboot failed: {status_flags}")
            """

            retry = False
            counter = counter + 1
            logger.info(f"Retry no. {counter} - waiting for a minute until all peers and orderers have started")
            time.sleep(30)

            for org in range(1, config['fabric_settings']['org_count'] + 1):
                for peer in range(0, config['fabric_settings']['peer_count']):
                    index_peer = config['peer_indices'][(org - 1) * config['fabric_settings']['peer_count'] + peer]

                    stdin, stdout, stderr = ssh_clients[index_peer].exec_command(f"cat /home/ubuntu/peer{peer}.org{org}.log")
                    # logger.info(f"Logs from starting peer{peer}.org{org}")

                    try:
                        out = stdout.readlines()
                        logger.info("stderr:")
                        logger.info(stderr.readlines())
                        if out == []:
                            pass
                        elif "Error while dialing dial tcp" in out[-1] or "docker: Error response from daemon" in out[-1] or "error waiting for container" in out[-1]:
                            if out == []:
                                logger.info("Empty")
                            elif "Error while dialing dial tcp" in out[-1]:
                                logger.info("Error while dialing dial tcp")
                                logger.info(out)
                            elif "docker: Error response from daemon" in out[-1]:
                                logger.info("docker: Error response from daemon")
                                logger.info(out)
                            elif "error waiting for container" in out[-1]:
                                logger.info("error waiting for container" in out[-1])
                                logger.info(out)
                            elif "See 'docker run --help'" in out[-1]:
                                logger.info("See 'docker run --help'")
                                logger.info(out)
                            else:
                                if "error waiting for container: context canceled" not in out[-1]:
                                    logger.info(out[-1])
                                else:
                                    try:
                                        logger.info(out[-1])
                                        logger.info(out[-2])
                                    except:
                                        pass
                                # logger.info(out[-1])
                            logger.info(f"Attempting to remove and restart peer{peer}.org{org}")
                            retry = True
                            stdin, stdout, stderr = ssh_clients[index_peer].exec_command(f"docker stop peer{peer}.org{org}.example.com && docker rm peer{peer}.org{org}.example.com")
                            stdout.readlines()
                            stderr.readlines()
                            # logger.info(stdout.readlines())
                            # logger.info(stderr.readlines())
                            channel = ssh_clients[index_peer].get_transport().open_session()
                            channel.exec_command(f"bash /home/ubuntu/start_peer.sh > /home/ubuntu/peer{peer}.org{org}.log 2>&1")
                        else:
                            pass
                            # logger.info(f"peer{peer}.org{org} has started successfully: Other output")
                            # logger.info(f"Not doing anything on peer{peer}.org{org}")

                    except Exception:
                        pass
                        # logger.info("Invalid byte")
                        # logger.info(f"Not doing anything on peer{peer}.org{org}")
                    # logger.info(stderr.readlines())

                    if config['fabric_settings']['database'] == "CouchDB":
                        index_db = config['db_indices'][(org - 1) * config['fabric_settings']['peer_count'] + peer]

                        stdin, stdout, stderr = ssh_clients[index_db].exec_command(f"cat /home/ubuntu/couchdb{peer}.org{org}.log")
                        # logger.info(f"Logs from starting couchdb{peer}.org{org}")

                        try:
                            out = stdout.readlines()
                            if out == []:
                                pass
                            elif "Error while dialing dial tcp" in out[-1] or "docker: Error response from daemon" in out[-1] or "error waiting for container" in out[-1]:
                                if out == []:
                                    pass
                                    # logger.info(out)
                                else:
                                    pass
                                    # logger.info(out[-1])
                                logger.info(f"Attempting to restart couchdb{peer}.org{org}")
                                retry = True
                                stdin, stdout, stderr = ssh_clients[index_db].exec_command(f"docker stop couchdb{peer}.org{org} && docker rm couchdb{peer}.org{org}")
                                stdout.readlines()
                                stderr.readlines()
                                # logger.info(stdout.readlines())
                                # logger.info(stderr.readlines())
                                channel = ssh_clients[index_db].get_transport().open_session()
                                channel.exec_command(f"bash /home/ubuntu/start_couchdb.sh > couchdb{peer}.org{org}.log 2>&1")
                            else:
                                pass
                                # logger.info(f"couchdb{peer}org{org} has started successfully: Other output")
                                # logger.info(f"Not doing anything on couchdb{peer}.org{org}")

                        except Exception:
                                pass
                            # logger.info("Invalid byte")
                            # logger.info(f"Not doing anything on couchdb{peer}.org{org}")
                        # logger.info(stderr.readlines())


            for orderer, index in enumerate(config['orderer_indices']):
                orderer = orderer + 1
                stdin, stdout, stderr = ssh_clients[index].exec_command(f"cat /home/ubuntu/orderer{orderer}.log")
                try:
                    out = stdout.readlines()
                    if out == []:
                        pass
                    elif "Error while dialing dial tcp" in out[-1] or "docker: Error response from daemon" in out[-1] or "error waiting for container" in out[-1]:
                        logger.info("docker: Error response from daemon" in out[-1])
                        logger.info("You cannot remove a running container" in out[-1])
                        logger.info("You cannot remove a running container" not in out[-1])
                        if out == []:
                                pass
                            # logger.info(out)
                        else:
                            # pass
                            logger.info(out[-1])
                        logger.info(f"Attempting to restart orderer{orderer}")
                        retry = True
                        stdin, stdout, stderr = ssh_clients[index].exec_command(f"docker stop orderer{orderer}.example.com && docker rm orderer{orderer}.example.com")
                        # stdout.readlines()
                        # stderr.readlines()
                        logger.info(stdout.readlines())
                        logger.info(stderr.readlines())
                        channel = ssh_clients[index].get_transport().open_session()
                        channel.exec_command(f"bash /home/ubuntu/start_orderer.sh > orderer{orderer}.log 2>&1")
                    else:
                        pass
                        # logger.info(f"orderer{orderer} has started successfully: Other output")
                        # logger.info(f"Not doing anything on orderer{orderer}")

                except Exception:
                    logger.info("Invalid byte")
                    logger.info(f"Not doing anything on orderer{orderer}")
                logger.info(stderr.readlines())

        logger.info("Waiting one last time before creating the channel(s)")
        time.sleep(30)

    @staticmethod
    def restart(node_handler, number_of_endorsers):

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        Fabric_Network.shutdown(node_handler)

        try:

            for index, _ in enumerate(ssh_clients):

                try:
                    stdin, stdout, stderr = ssh_clients[index].exec_command("docker stop $(docker ps -a -q); docker rm -f $(docker ps -a -q) ; docker rmi $(docker images | grep 'my-net' | awk '{print $1}') || echo 'Stopping worked'")
                    logger.info(stdout.readlines())
                    logger.info(stderr.readlines())

                    # stdin, stdout, stderr = ssh_clients[index].exec_command("docker volume rm $(docker volume ls -q)")
                    # wait_and_log(stdout, stderr)

                    stdin, stdout, stderr = ssh_clients[index].exec_command("docker ps -a && docker volume ls && docker images")
                    logger.info(stdout.readlines())
                    logger.info(stderr.readlines())

                    ssh_clients[index].exec_command("sudo reboot")

                except Exception as e:
                    logger.exception(e)


            logger.info("Waiting till all machines have rebooted")
            time.sleep(10)

            status_flags = wait_till_done(config, ssh_clients, config['ips'], 10 * 60, 10, "/var/log/user_data_success.log", False, 10 * 60, logger)

            print(status_flags)

            if False in status_flags:
                    raise Exception("Problems with rebooting")

            node_handler.close_ssh_scp_clients()
            node_handler.refresh_ssh_scp_clients()

            ssh_clients = node_handler.ssh_clients
            scp_clients = node_handler.scp_clients

            stdin, stdout, stderr = ssh_clients[index].exec_command("docker volume rm $(docker volume ls -q)")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())
            stdin, stdout, stderr = ssh_clients[index].exec_command("docker ps -a && docker volume ls ")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())
            Fabric_Network.start_docker_containers(config, logger, ssh_clients, scp_clients)

            Fabric_Network.setup_network(config, ssh_clients, scp_clients, logger, "network_setup")

            Fabric_Network.install_chaincode(node_handler, number_of_endorsers)

        except Exception as e:
            logger.exception(e)
            Fabric_Network.shutdown(node_handler)
            Fabric_Network.start_docker_containers(config, logger, ssh_clients, scp_clients)

    @staticmethod
    def push_stuff(config, ssh_clients, scp_clients, indices_sources, indices_targets, logger):
        # logger.debug(f"Sources: {indices_sources}, targets: {indices_targets}")

        jobs = []
        for index, index_source in enumerate(indices_sources):
            # logger.debug(f"Creating thread {index} for pushing from {index_source} to {indices_targets[index]}")
            thread = threading.Thread(target=Fabric_Network.push_stuff_single(config, ssh_clients, scp_clients, index_source, indices_targets[index], logger))
            # logger.debug(f"Starting thread {index}")
            thread.start()
            jobs.append(thread)

        for j in jobs:
            # logger.debug(f"Joining thread {j}")
            j.join()

    @staticmethod
    def push_chaincode(config, ssh_clients, scp_clients, indices_sources, indices_targets, logger):
        # logger.debug(f"Sources: {indices_sources}, targets: {indices_targets}")

        jobs = []
        for index, index_source in enumerate(indices_sources):
            # logger.debug(f"Creating thread {index} for pushing from {index_source} to {indices_targets[index]}")
            thread = threading.Thread(target=Fabric_Network.push_chaincode_single(config, ssh_clients, scp_clients, index_source, indices_targets[index], logger))
            # logger.debug(f"Starting thread {index}")
            thread.start()
            jobs.append(thread)

        for j in jobs:
            # logger.debug(f"Joining thread {j}")
            j.join()

    @staticmethod
    def push_stuff_single(config, ssh_clients, scp_clients, index_source, index_target, logger):
        logger.debug(f"Starting to push from index {index_source} to index {index_target}")
        # deleting data at the vm associated with source_index and copying it to the vm associated with the target index
        # use scp -v for verbose mode

        stdin, stdout, stderr = ssh_clients[index_source].exec_command(
            f"ssh -o 'StrictHostKeyChecking no' -i /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem ubuntu@{config['priv_ips'][index_target]} 'sudo rm -rf /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts && echo Success'")
        stdout.readlines()
        stderr.readlines()
        # logger.info(stdout.readlines())
        # logger.info(stderr.readlines())
        stdin, stdout, stderr = ssh_clients[index_source].exec_command(
            f"scp -o 'StrictHostKeyChecking no' -ri /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config ubuntu@{config['priv_ips'][index_target]}:/data/fabric-samples/Build-Multi-Host-Network-Hyperledger && sudo chmod 600 /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem && echo Success")
        stdout.readlines()
        stderr.readlines()
        # logger.info(stdout.readlines())
        # logger.info(stderr.readlines())
        stdin, stdout, stderr = ssh_clients[index_source].exec_command(
            f"scp -o 'StrictHostKeyChecking no' -ri /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts ubuntu@{config['priv_ips'][index_target]}:/data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo Success")
        stdout.readlines()
        stderr.readlines()
        # logger.info(stdout.readlines())
        # logger.info(stderr.readlines())

        Fabric_Network.push_chaincode_single(config, ssh_clients, scp_clients, index_source, index_target, logger)
        # logger.debug(f"Successfully pushed to index {index_target}")

    @staticmethod
    def push_chaincode_single(config, ssh_clients, scp_clients, index_source, index_target, logger):
        stdin, stdout, stderr = ssh_clients[index_source].exec_command(
            f"scp -o 'StrictHostKeyChecking no' -ri /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode ubuntu@{config['priv_ips'][index_target]}:/data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo Success")
        stdout.readlines()
        stderr.readlines()
        # logger.info(stdout.readlines())
        # logger.info(stderr.readlines())

    @staticmethod
    def upload_chaincode(config, ssh_clients, scp_clients, logger):
        dir_name = os.path.dirname(os.path.realpath(__file__))

        logger.info("Pushing chaincode to all nodes")
        indices = unique(config['orderer_indices'] + config['peer_indices'])
        logger.info("Indices to be pushed to: " + indices)

        # pushing the ssh-key and the chaincode on the first vm
        scp_clients[0].put(f"{config['priv_key_path']}", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem")
        scp_clients[0].put(f"{dir_name}/chaincode/benchcontract", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode", recursive=True)
        Fabric_Network.write_collections(config, logger)
        scp_clients[0].put(f"{config['exp_dir']}/setup/collections.json", "/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode/benchcontract")
        logger.debug("Successfully pushed to index 0.")

        finished_indices = [indices[0]]
        remaining_indices = indices[1:len(indices)]
        while remaining_indices != []:
            n_targets = min(len(finished_indices), len(remaining_indices))
            indices_sources = finished_indices[0:n_targets]
            indices_targets = remaining_indices[0:n_targets]

            Fabric_Network.push_chaincode(config, ssh_clients, scp_clients, indices_sources, indices_targets, logger)

            finished_indices = indices_sources + indices_targets
            remaining_indices = remaining_indices[n_targets:]

        # deleting the ssh-keys after having finished
        for _, index in enumerate(indices):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"rm /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/key.pem")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

    @staticmethod
    def setup_network(config, ssh_clients, scp_clients, logger, name, number_of_endorsers=None):

        logger.info(f"Creating script for {name}")
        Fabric_Network.write_script(config, logger, name, number_of_endorsers)

        my_net = "my-net"

        index_last_node = config['peer_indices'][-1]
        # Creating script and pushing it to the last node


        if name == "network_setup":
            logger.debug(f"Executing script on {config['ips'][index_last_node]}  which creates channel and adds all peers to channel - can take some minutes")

        elif name == "chaincode_installation":
            logger.debug(f"Executing script on {config['ips'][index_last_node]}  which installs and instantiates all chaincode - can take some minutes")

        stdin, stdout, stderr = ssh_clients[index_last_node].exec_command("rm -f /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")
        stdout.readlines()

        # logger.debug(stdout.readlines())
        # logger.debug(stdout.readlines())
        scp_clients[index_last_node].put(f"{config['exp_dir']}/setup/{name}.sh", f"/data/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/{name}.sh")

        # Setting up configuration of cli like with docker compose
        string_cli_base = ""
        string_cli_base = string_cli_base + f" --network='{my_net}' --name cli -p 12051:7051 -p 12053:7053"
        string_cli_base = string_cli_base + f" -e GOPATH=/opt/gopath"
        string_cli_base = string_cli_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"

        string_cli_link = ""
        for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
            string_cli_link = string_cli_link + f" --link orderer{orderer}.example.com:orderer{orderer}.example.com"

        for org in range(1, config['fabric_settings']['org_count'] + 1):
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
        if config['fabric_settings']['tls_enabled']:
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
        string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config:/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config"
        string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts:/opt/gopath/src/github.com/hyperledger/fabric/peer/scripts/"
        string_cli_v = string_cli_v + f" -v /data/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts:/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts"
        string_cli_v = string_cli_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

        # execute script.sh on last node

        for channel in range(config['fabric_settings']['channel_count']):
            stdin, stdout, stderr = ssh_clients[index_last_node].exec_command(
                f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_cli_base + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash -c '(ls -la && cd scripts && ls -la && chmod 777 {name}.sh && ls -la && cd .. && ./scripts/{name}.sh mychannel{channel + 1})' |& tee /home/ubuntu/setup_mychannel{channel + 1}.log)")
            out = stdout.readlines()

            # save the cli command on the last node and save it in exp_dir
            ssh_clients[index_last_node].exec_command(f"(cd /data/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_cli_base + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash\" > /data/cli2.sh)")

            if out[len(out) - 1] == "========= All GOOD, script completed =========== \n":
                logger.info("")
                logger.info(f"**************** !!! Fabric network formation for channel << mychannel{channel + 1} >> was successful !!! *********************")
                logger.info("")
            else:
                logger.info("")
                logger.info(f"*******************!!! ERROR: Fabric network formation failed on channel << mychannel{channel + 1} >> !!! *********************")
                for index, _ in enumerate(out):
                    logger.debug(out[index].replace("\n", ""))

                raise Exception("Blockchain did not start properly - Omitting or repeating")

    @staticmethod
    def install_chaincode(node_handler, number_of_endorsers=None):
        Fabric_Network.setup_network(node_handler.config, node_handler.ssh_clients, node_handler.scp_clients, node_handler.logger, "chaincode_installation", number_of_endorsers)


    @staticmethod
    def find_leader(config, ssh_clients, scp_clients, logger):

        leaders = []
        blocknumbers = []

        for index, node in enumerate(config['orderer_indices']):

            stdin, stdout, stderr = ssh_clients[node].exec_command(f"a=3 && cat orderer{index+1}.log " + "| grep 'Start accepting requests as Raft leader' | grep mychannel | awk -F ' ' '{print $NF-$a}'")
            out = stdout.readlines()
            logger.info(out)
            logger.info(stderr.readlines())

            if len(out) != 0:
                leaders.append(node)
                blocknumbers.append(out[-1].replace('\n', ""))

            if len(out) > 1:
                logger.info(f"Multiple elections found on {node}")

        logger.info(f"Leaders: {leaders}")
        logger.info(f"Raft leaders found: {leaders} at {[config['ips'][i] for i in leaders]}")

        if len(leaders) == 0:
            logger.info("No leader found")
            return None

        elif len(leaders) == 1:
            logger.info(f"Unique leader found: {leaders[0]} at {config['ips'][leaders[0]]}")
            return leaders[0]

        elif len(leaders) > 1:

            # search for the highest entry in blocknumbers
            logger.info(f"Blocknumbers: {blocknumbers}")
            latest = max(blocknumbers)
            index = np.where(leaders == latest)
            logger.info(f"Index: {index}")
            return leaders[index]


    @staticmethod
    def shutdown_raft_leader(config, ssh_clients, scp_clients, logger):

        leader_index = config['orderer_indices'][Fabric_Network.find_leader(config, ssh_clients, scp_clients, logger)]

        logger.info(f"Crashing leader node with index {leader_index} and ip {config['ips'][leader_index]}")

        try:
            stdin, stdout, stderr = ssh_clients[leader_index].exec_command("docker stop $(docker ps -a -q) && docker rm -f $(docker ps -a -q) && docker rmi $(docker images | grep 'my-net' | awk '{print $1}'); rm /home/ubuntu/orderer*.log && sudo rm -r ./var/lib/docker/volumes/afe902cdfb0eb2d7bb0284743e8652278753d75ef7732e3702e20687afb4013b/")
            wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[leader_index].exec_command("docker volume rm $(docker volume ls -q)")
            wait_and_log(stdout, stderr)

            stdin, stdout, stderr = ssh_clients[leader_index].exec_command("docker ps -a && docker volume ls && docker images")
            wait_and_log(stdout, stderr)

        except Exception as e:

            ssh_clients[leader_index].exec_command("sudo reboot")

        logger.info("Crashed leader successfully")
        time.sleep(10)

        logger.info("Who is the new leader?")
        new_leader = Fabric_Network.find_leader(config, ssh_clients, scp_clients, logger)

        logger.info(f"The new leader is {new_leader} at ip {config['ips'][new_leader]}")

        return leader_index


    @staticmethod
    def restart_orderer(config, ssh_clients, scp_clients, logger, index):

        logger.info(f"Restarting orderer{index+1} at {config['ips'][config['orderer_indices'][index]]}")
        channel = ssh_clients[config['orderer_indices'][index]].get_transport().open_session()
        channel.exec_command("bash /home/ubuntu/start_orderer.sh")

    @staticmethod
    def stopstart_orderer(config, ssh_clients, scp_clients, logger, index):

        time.sleep(10)

        logger.info(f"Restarting orderer{index+1} at {config['ips'][config['orderer_indices'][index]]}")
        stdin, stdout, stderr = ssh_clients[config['orderer_indices'][index].exec_command(f"docker stop orderer{index+1}.example.com")]
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        time.sleep(10)

        channel = ssh_clients[config['orderer_indices'][index]].get_transport().open_session()
        channel.exec_command("bash /home/ubuntu/start_orderer.sh")

    @staticmethod
    def stopstart_leader(node_handler):

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        time.sleep(10)

        leader_index = config['orderer_indices'][Fabric_Network.find_leader(config, ssh_clients, scp_clients, logger)]

        logger.info(f"Restarting leader, which is currently orderer{leader_index + 1} at {config['ips'][config['orderer_indices'][leader_index]]}")
        stdin, stdout, stderr = ssh_clients[config['orderer_indices'][leader_index]].exec_command(f"docker stop orderer{leader_index + 1}.example.com")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        time.sleep(10)

        channel = ssh_clients[config['orderer_indices'][leader_index]].get_transport().open_session()
        channel.exec_command("bash /home/ubuntu/start_orderer.sh")


