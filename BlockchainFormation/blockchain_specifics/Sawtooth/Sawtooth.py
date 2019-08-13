import os
import sys
import json
import time
from web3 import Web3

def sawtooth_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the sawtooth specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    # adding "true" number of blockchain nodes and their ips
    config['node_count'] = config['vm_count']
    config['node_priv_ips'] = config['priv_ips']
    config['node_pub_ips'] = config['pub_ips']

    for index, _ in enumerate(config['pub_ips']):
        # get account from all instances
        scp_clients[index].get("/var/log/sawtooth", f"{config['exp_dir']}/sawtooth_logs/sawtooth_logs_node_{index}", recursive=True)
        scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


def sawtooth_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """

    dir_name = os.path.dirname(os.path.realpath(__file__))

    logger.info("Creating directories for saving data and logs locally")
    os.mkdir(f"{config['exp_dir']}/sawtooth_logs")

    logger.info("Changing permissions of log directory such that logs can be pulled via scp later")
    for index, _ in enumerate(config['priv_ips']):
        os.mkdir(f"{config['exp_dir']}/sawtooth_logs/sawtooth_logs_node_{index}")
        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo chown -R sawtooth:ubuntu /var/log/sawtooth")
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

    logger.debug("Checking whether installation on first node was successfull")
    stdin, stdout, stderr = ssh_clients[0].exec_command("dpkg -l '*sawtooth*'")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    logger.info("Doing special config stuff for first node")
    logger.debug("Creating genesis config on first node")

    # Creating config-genesis.batch
    stdin, stdout, stderr = ssh_clients[0].exec_command("sudo -u sawtooth sawset genesis --key /etc/sawtooth/keys/validator.priv -o /home/sawtooth/temp/config-genesis.batch")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    # Creating config-consensus.batch
    stdin, stdout, stderr = ssh_clients[0].exec_command('sudo -u sawtooth sawset proposal create --key /etc/sawtooth/keys/validator.priv -o /home/sawtooth/temp/config-consensus.batch sawtooth.consensus.algorithm.name=PoET sawtooth.consensus.algorithm.version=0.1 sawtooth.poet.report_public_key_pem="$(cat /etc/sawtooth/simulator_rk_pub.pem)" sawtooth.poet.valid_enclave_measurements=$(poet enclave measurement) sawtooth.poet.valid_enclave_basenames=$(poet enclave basename)')
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    # Creating poet.batch
    stdin, stdout, stderr = ssh_clients[0].exec_command("sudo -u sawtooth poet registration create --key /etc/sawtooth/keys/validator.priv -o /home/sawtooth/temp/poet.batch")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    # Creating poet-settings.batch
    stdin, stdout, stderr = ssh_clients[0].exec_command("sudo -u sawtooth sawset proposal create --key /etc/sawtooth/keys/validator.priv -o /home/sawtooth/temp/poet-settings.batch sawtooth.poet.target_wait_time=5 sawtooth.poet.initial_wait_time=25 sawtooth.publisher.max_batches_per_block=100")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    # Creating genesis block using the just created config.batches
    stdin, stdout, stderr = ssh_clients[0].exec_command("sudo -u sawtooth sawadm genesis /home/sawtooth/temp/config-genesis.batch /home/sawtooth/temp/config-consensus.batch /home/sawtooth/temp/poet.batch /home/sawtooth/temp/poet-settings.batch")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    logger.info("Adapting config (.toml)-file for validator, starting sawtooth-services and finalizing setup on all nodes")
    for index1, ip1 in enumerate(config['priv_ips']):

        # Creating string for binding specification and replace substitute_binding
        binding_string = f'\\"network:tcp://{ip1}:8800\\",'
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_bind#" + binding_string + "#g /home/ubuntu/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        # Creating string for endpoint speficifation and replace substitute_endpoint
        endpoint_string = f'endpoint\ =\ \\"tcp://{ip1}:8800\\"'
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_endpoint#" + endpoint_string + "#g /home/ubuntu/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

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

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_peers#" + peer_string + "#g /home/ubuntu/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        # Adjusting minimum and maximum peer connectivity
        min_connectivity_string = f"{len(config['priv_ips']) - 1}"
        max_connectivity_string = f"{2 * (len(config['priv_ips']) - 1)}"
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_min_connectivity#" + min_connectivity_string + "#g /home/ubuntu/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_max_connectivity#" + max_connectivity_string + "#g /home/ubuntu/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        # adjusting REST-API config
        stdin, stdout, stderr = ssh_clients[index1].exec_command("sed -i -e s#substitute_local_private_ip#" + ip1 + "#g /home/ubuntu/rest_api.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        # Replacing the configs in /etc/sawtooth by the customized configs

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /home/ubuntu/validator.toml /etc/sawtooth/validator.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /home/ubuntu/rest_api.toml /etc/sawtooth/rest_api.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo mv /home/ubuntu/cli.toml /etc/sawtooth/cli.toml")
        logger.debug("".join(stdout.readlines()))
        logger.debug("".join(stderr.readlines()))

        # stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo chown root:sawtooth /etc/sawtooth/validator.toml")
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

        # stdin, stdout, stderr = ssh_clients[index1].exec_command("sudo chmod 640 /etc/sawtooth/validator.toml")
        # logger.debug("".join(stdout.readlines()))
        # logger.debug("".join(stderr.readlines()))

        # Starting all services
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-rest-api.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-validator.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-settings-tp.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-identity-tp.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-intkey-tp-python.service")

        # channel = ssh_clients[index1].get_transport().open_session()
        # channel.exec_command("sudo systemctl start sawtooth-xo-tp-python.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-poet-validator-registry-tp.service")

        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("sudo systemctl start sawtooth-poet-engine.service")

        logger.debug("Installing BenchContract...")
        scp_clients[index1].put(dir_name + "/processor", "/home/ubuntu", recursive=True)
        channel = ssh_clients[index1].get_transport().open_session()
        channel.exec_command("screen -S bench python3 /home/ubuntu/processor/main.py")

    logger.info("Waiting for 10s until all nodes have started")
    time.sleep(10)
    logger.info("All nodes have started")
    logger.info("Checking whether setup has been successful by searching for every peer in sawtooth peer list")

    boo1 = True
    for index, ip in enumerate(config['pub_ips']):

        stdin, stdout, stderr = ssh_clients[index].exec_command(f"sawtooth peer list --url http://{config['priv_ips'][index]}:8008")
        out = stdout.readlines()
        try:
            peer_list = set(out[0].replace("\n", "").split(","))
            if len(peer_list) != len(config['priv_ips'])-1:
                boo1 = False
                logger.info(f"Node {index} on IP {ip} has not started properly")

        except:
            logger.info(f"Something went wrong - sawtooth peer list not working")
            boo1 = False

    if boo1 == True:
            logger.info(f"All nodes seem to have started properly")

    logger.info("Checking whether intkey is working on every peer by making one set operation and reading on all nodes")
    ssh_clients[len(config['priv_ips'])-1].exec_command(f"intkey set val1 100 --url http://{config['priv_ips'][0]}:8008")
    time.sleep(5)
    boo2 = True
    for index, ip in enumerate(config['priv_ips']):
        stdin, stdout, stderr = ssh_clients[index].exec_command(f"intkey show val1 --url http://{config['priv_ips'][index]}:8008")
        out = stdout.readlines()
        try:
            if (out[0].replace("\n", "") != "val1: 100"):
                boo2 = False
                logger.info(f"Node {index} on IP {ip} not working properly")
        except:
            logger.info("Something went wrong - sawtooth intkey is not working")
            boo2 = False

    if boo2 == True:
        logger.info("Intkey working properly on all nodes")

    if boo1 == True and boo2 == True:
        logger.info("Sawtooth network setup was successful")
    else:
        logger.info("Sawtooth network setup was NOT successful")

    logger.info("Checking whether BenchContract is working properly on every peer by making one set operation and reading on all nodes")
    

""" THIS IS CLIENT-STUFF
    # setting up api stuff on first node
    scp_clients[0].put("/home/user/ec2_automation/blockchain_specifics/Sawtooth/api", "/home/ubuntu", recursive=True)
    stdin, stdout, stderr = ssh_clients[0].exec_commnand("nvm install node")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    stdin, stdout, stderr = ssh_clients[0].exec_command("(mv /home/ubuntu/api/request_raw.js /home/ubuntu/api/request.js && cd api && npm install &> api.log)")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    stdin, stdout, stderr = ssh_clients[0].exec_command(f"sed -i -e 's/substitute_priv_ip/{config['pub_ips'][0]}/g' /home/ubuntu/api/request.js")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())
    stdin, stdout, stderr = ssh_clients[0].exec_command("(cd api && node request.js &> api.log")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())

    logger.info("Done")
"""
