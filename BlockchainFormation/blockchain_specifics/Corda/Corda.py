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



import os
import time
import numpy as np
from BlockchainFormation.utils.utils import *

import hashlib


def corda_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the corda specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    pass


def corda_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the corda specific startup script
    :return:
    """

    logger.info(f"Started Corda")

    logger.info("Uploading the customized config.gradle and generating node documents")
    stdin, stdout, stderr = ssh_clients[0].exec_command("rm /data/samples/cordapp-example/workflows-kotlin/config.gradle")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    # wait_and_log(stdout, stderr)
    scp_clients[0].put(f"{config['exp_dir']}/setup/config.gradle", "/data/samples/cordapp-example/workflows-kotlin/config.gradle")
    stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/samples/cordapp-example && ./gradlew deployNodes)")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    # wait_and_log(stdout, stderr)

    logger.info("Getting the generated files and distributing them to the nodes")
    scp_clients[0].get("/data/samples/cordapp-example/workflows-kotlin/build/nodes", f"{config['exp_dir']}/setup", recursive=True)
    stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/samples/cordapp-example/workflows-kotlin/build/nodes && rm runnodes runnodes.bat runnodes.jar Party*_node.conf)")
    logger.debug(stdin.readlines())
    logger.debug(stderr.readlines())
    stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/samples/cordapp-example/workflows-kotlin/build/nodes && rm -r Party*")
    logger.debug(stdin.readlines())
    logger.debug(stderr.readlines())
    for node, _ in enumerate(config['priv_ips']):
        scp_clients[node].put(f"{config['exp_dir']}/setup/Party{node}", "/data/samples/cordapp-example/workflows-kotlin/build/nodes", recursive=True)
        scp_clients[node].put(f"{config['exp_dir']}/setup/Party{node}_node.conf", "/data/samples/cordapp-example/workflows-kotlin/build/nodes")
        
    logger.info("Starting all nodes")
    channels = []
    for node, _ in enumerate(config['priv_ips']):
        channel = ssh_clients[node].get_transport().open_session()
        channel.exec_command(f"(cd /data/samples/cordapp-example && ./gradlew runParty{node}Server )")
        channels.append(channel)

    # Checking whether the system has connected








    for node, ip in enumerate(config['priv_ips']):
        # change nodes port
        stdin, stdout, stderr = ssh_clients[node].exec_command(f"sed -i -e 's/localhost/{ip}/g' /data/corda/cordapp-example/workflows-kotlin/build/nodes/PartyX/node.conf")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())
        # wait_and_log(stdout, stderr)

        # start node
        channel = ssh_clients[node].get_transport().open_session()
        channel.exec_command("(cd /data/corda/cordapp-example && workflows-kotlin/build/nodes/runnodes")

    # transaction with node terminal
    stdin, stdout, stderr = ssh_clients[0].exec_command('(cd /data/corda/cordapp-example/ && flow start ExampleFlow$Initiator iouValue: 50, otherParty: "O=PartyB,L=New York,C=US")')



def corda_restart(config, logger, ssh_clients, scp_clients):
    """
    Runs the corda specific startup script
    :return:
    """

    pass

def write_config(config, logger):

    dir_name = os.path.dirname(os.path.realpath(__file__))
    os.system(f"cp {dir_name}/setup/config_raw.gradle {config['exp_dir']}/setup/config.gradle")

    f = open(f"{config['exp_dir']}/setup/config.gradle", "a")
    
    f.write("task deployNodes(type: Cordform, dependsOn: ['jar']) {\n")
    f.write("    nodeDefaults {\n")
    f.write("        cordapp project(':contracts-kotlin'\n")
    f.write("    }\n")

    for node, ip in enumerate(config['priv_ips']):
        f.write("    node {\n")
        f.write(f"        name 'O=Notary{node},L=London,C=GB'\n")
        f.write("        notary = [validating : false]\n")
        f.write("        p2pPort 10000\n")
        f.write("        rpcSettings {\n")
        f.write(f"            address('{ip}:10001')\n")
        f.write(f"            adminAddress('{ip}:10002')\n")
        f.write("        }\n")
        f.write("        projectCordapp {\n")
        f.write("            deploy = false\n")
        f.write("        }\n")
        f.write("        cordapps.clear()\n")
        f.write("    }\n")


        f.write("    node {\n")
        f.write(f"        name 'O=Party{node},L=London,C=GB'\n")
        f.write("        p2pPort 10000\n")
        f.write("        rpcSettings {\n")
        f.write(f"            address('{ip}:10001')\n")
        f.write(f"            adminAddress('{ip}:10001')\n")
        f.write("        }\n")
        f.write("        rpcUsers = [[user: 'user1', 'password': 'test', 'permissions': ['ALL']]]\n")
        f.write("    }\n")
        f.write("}\n")

    f.close()

