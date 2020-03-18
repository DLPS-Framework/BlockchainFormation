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

    config['node_indices'] = list(range(1, config['vm_count']))
    config['group_indices'] = [config['node_indices']]

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
            logger.debug(out)
            logger.debug("".join(stderr.readlines()))

    config['join_command'] = "sudo " + join_command

    # Name of the swarm network
    my_net = "my-net"
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo docker network create --subnet 10.10.0.0/16 --attachable --driver overlay {my_net}")
    out = stdout.readlines()
    logger.debug(out)
    logger.debug("".join(stderr.readlines()))

    time.sleep(5)

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
        logger.info(f"Expected length: {len(config['priv_ips']) + 1}, actual length: {len(out)}")
        sys.exit("Fatal error when performing docker swarm setup")

    logger.info(f"Started Corda")

    logger.info("Uploading the customized build.gradle and generating node documents")
    stdin, stdout, stderr = ssh_clients[0].exec_command("rm /data/samples/cordapp-example/workflows-kotlin/build.gradle")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    # wait_and_log(stdout, stderr)

    # Creating node certificate and startup scripts
    write_config_node(config, logger)

    # Creating configs for the clients (Corda spring servers)
    for client, _ in enumerate(config['priv_ips']):
        if client != 0:
            write_config_client(config, client, logger)

    # Pushing the network config to the first node and creating all files which are relevant for Corda setup there
    logger.info(f"Pushing build.gradle to the first node on {config['ips'][0]}")
    scp_clients[0].put(f"{config['exp_dir']}/setup/build.gradle", "/data/samples/cordapp-example/workflows-kotlin/build.gradle")
    stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/samples/cordapp-example && ./gradlew deployNodes)")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    # wait_and_log(stdout, stderr)

    logger.info("Getting the generated files and distributing them to the nodes")
    scp_clients[0].get("/data/samples/cordapp-example/workflows-kotlin/build/nodes", f"{config['exp_dir']}/setup", recursive=True)
    stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/samples/cordapp-example/workflows-kotlin && rm -r build)")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    for node, _ in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[node].exec_command("(cd /data/samples/cordapp-example/workflows-kotlin && rm build.gradle && mkdir build && cd build && mkdir nodes && cd /data/samples/cordapp-example/clients && rm build.gradle)")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        if node == 0:
            scp_clients[node].put(f"{config['exp_dir']}/setup/nodes/Notary", "/data/samples/cordapp-example/workflows-kotlin/build/nodes", recursive=True)
            scp_clients[node].put(f"{config['exp_dir']}/setup/nodes/Notary_node.conf", "/data/samples/cordapp-example/workflows-kotlin/build/nodes")
            logger.info(f"Pushed all relevant files to node {node} on ip {config['priv_ips'][node]}")
        else:
            scp_clients[node].put(f"{config['exp_dir']}/setup/nodes/Party{node}", "/data/samples/cordapp-example/workflows-kotlin/build/nodes", recursive=True)
            scp_clients[node].put(f"{config['exp_dir']}/setup/nodes/Party{node}_node.conf", "/data/samples/cordapp-example/workflows-kotlin/build/nodes")
            scp_clients[node].put(f"{config['exp_dir']}/setup/build_client{node}.gradle", "/data/samples/cordapp-example/clients/build.gradle")
            logger.info(f"Pushed all relevant files to node {node} on ip {config['priv_ips'][node]}")

    start_corda_nodes(config, logger, ssh_clients)


def start_corda_nodes(config, logger, ssh_clients):
    """
    Starts the Corda node and its server
    :param config:
    :param logger:
    :param ssh_clients:
    """

    logger.info("Starting all nodes")
    channels = []
    for node, _ in enumerate(config['priv_ips']):
        if node != 0:
            channel = ssh_clients[node].get_transport().open_session()
            channel.exec_command(f"(cd /data/samples/cordapp-example/workflows-kotlin/build/nodes/Party{node} && java -jar corda.jar >> ~/node.log 2>&1)")
            channels.append(channel)

    logger.info("Starting all servers")
    for node, _ in enumerate(config['priv_ips']):
        if node != 0:
            channel = ssh_clients[node].get_transport().open_session()
            channel.exec_command(f"(cd /data/samples/cordapp-example && ./gradlew runServer >> ~/server.log 2>&1)")

    # TODO Find some way to see precisely when the server startup has finished
    logger.info("Waiting for the servers startup to finish")
    time.sleep(180)

    logger.info("Testing an iou transaction locally (at least 3 nodes required")
    stdin, stdout, stderr = ssh_clients[1].exec_command(f"curl -i -X POST 'http://localhost:50005/api/example/create-iou?iouValue=12&partyName=O=Party2,L=London,C=GB' -H 'Content-Type: application/x-www-form-urlencoded'")
    logger.info(stdout.readlines())
    logger.info(stderr.readlines())


def corda_restart(config, logger, ssh_clients, scp_clients):
    """
    Runs the corda specific startup script
    :return:
    """

    corda_shutdown(config, logger, ssh_clients, scp_clients)
    start_corda_nodes(config, logger, ssh_clients, scp_clients)


def write_config_node(config, logger):
    """
    Creates the config describing the corda network
    :param config:
    :param logger:
    """
    dir_name = os.path.dirname(os.path.realpath(__file__))

    os.system(f"cp {dir_name}/setup/build_raw_node.gradle {config['exp_dir']}/setup/build.gradle")

    f = open(f"{config['exp_dir']}/setup/build.gradle", "a")

    f.write("task deployNodes(type: Cordform, dependsOn: ['jar']) {\n")
    f.write("    nodeDefaults {\n")
    f.write("        cordapp project(':contracts-kotlin')\n")
    f.write("    }\n")

    for node, ip in enumerate(config['priv_ips']):

        if node == 0:

            f.write("    node {\n")
            f.write(f"        name 'O=Notary,L=London,C=GB'\n")
            f.write(f"        notary = [validating : false]\n")
            f.write(f"        p2pAddress ('{ip}:10000')\n")
            f.write("        rpcSettings {\n")
            f.write(f"            address('{ip}:10001')\n")
            f.write(f"            adminAddress('localhost:10002')\n")
            f.write("        }\n")
            f.write("        projectCordapp {\n")
            f.write(f"            deploy = false\n")
            f.write("        }\n")
            f.write(f"        cordapps.clear()\n")
            f.write("    }\n")

        else:

            f.write("    node {\n")
            f.write(f"        name 'O=Party{node},L=London,C=GB'\n")
            f.write(f"        p2pAddress ('{ip}:10000')\n")
            f.write("        rpcSettings {\n")
            f.write(f"            address('{ip}:10001')\n")
            f.write(f"            adminAddress('localhost:10002')\n")
            f.write("        }\n")
            f.write(f"        rpcUsers = [[user: 'user1', 'password': 'test', 'permissions': ['ALL']]]\n")
            f.write("    }\n")

    f.write("}\n")

    f.close()


def write_config_client(config, client, logger):
    """
    Creates the configuration of a specific corda spring server (REST API)
    :param config:
    :param client:
    :param logger:
    """
    dir_name = os.path.dirname(os.path.realpath(__file__))

    os.system(f"cp {dir_name}/setup/build_raw_client.gradle {config['exp_dir']}/setup/build_client{client}.gradle")

    ip = config['priv_ips'][client]

    f = open(f"{config['exp_dir']}/setup/build_client{client}.gradle", "a")

    f.write("task runServer(type: JavaExec, dependsOn: jar) {\n")
    f.write("    classpath = sourceSets.main.runtimeClasspath\n")
    f.write("    main = 'com.example.server.ServerKt'\n")
    f.write(f"    args '--server.rpc.host={ip}', '--server.port=50005', '--config.rpc.host={ip}', '--config.rpc.port=10001', '--config.rpc.username=user1', '--config.rpc.password=test'\n")
    f.write("}\n")

    f.close()
