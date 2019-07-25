import os
import sys
import subprocess
import json
import time
import numpy as np
import paramiko
import boto3
from scp import SCPClient


def fabric_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the fabric specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['priv_ips']):
        scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs")
        scp_clients[index].get("/var/log/user_data.log",
                               f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


def fabric_startup(ec2_instances, config, logger, ssh_clients, scp_clients):
    dir_name = os.path.dirname(os.path.realpath(__file__))
    
    # create directories for the fabric logs and all the setup data (crypto-stuff, config files and scripts which are exchanged with the VMs)
    os.mkdir(f"{config['exp_dir']}/fabric_logs")
    os.mkdir(f"{config['exp_dir']}/api")

    # Rebooting all machines
    ssh_clients, scp_clients = reboot_all(ec2_instances, config, logger, ssh_clients, scp_clients)

    # Creating docker swarm
    logger.info("Preparing & starting docker swarm")

    stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm init")
    out = stdout.readlines()
    for index, _ in enumerate(out):
        logger.debug(out[index].replace("\n", ""))

    logger.debug("".join(stderr.readlines()))

    stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm join-token manager")
    out = stdout.readlines()
    logger.debug(out)
    logger.debug("".join(stderr.readlines()))
    join_command = out[2].replace("    ", "").replace("\n", "")

    for index, _ in enumerate(config['priv_ips']):

        if index != 0:
            stdin, stdout, stderr = ssh_clients[index].exec_command("sudo " + join_command)
            logger.debug(stdout.readlines())
            logger.debug("".join(stderr.readlines()))

    # Name of the swarm network
    my_net = "my-net"
    stdin, stdout, stderr = ssh_clients[0].exec_command(
        f"sudo docker network create --attachable --driver overlay {my_net}")
    out = stdout.readlines()
    logger.debug(out)
    logger.debug("".join(stderr.readlines()))
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

    logger.info("Creating crypto-config.yaml and pushing it to first node")
    write_crypto_config(config, logger)

    stdin, stdout, stderr = ssh_clients[0].exec_command(
        "rm -f /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config.yaml")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))
    scp_clients[0].put(f"{config['exp_dir']}/setup/crypto-config.yaml",
                       "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config.yaml")

    logger.info("Creating configtx and pushing it to first node")
    write_configtx(config)

    stdin, stdout, stderr = ssh_clients[0].exec_command(
        "rm -f /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/configtx.yaml")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))
    scp_clients[0].put(f"{config['exp_dir']}/setup/configtx.yaml",
                       "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/configtx.yaml")

    logger.info("Creating bmhn.sh and pushing it to first node")
    os.system(
        f"cp {dir_name}/setup/bmhn.sh {config['exp_dir']}/setup/bmhn.sh")
    stdin, stdout, stderr = ssh_clients[0].exec_command(
        "rm -f /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/bmhn.sh")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))
    scp_clients[0].put(f"{config['exp_dir']}/setup/bmhn.sh",
                       "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/bmhn.sh")

    logger.info("Creating crypto-stuff on first node by executing bmhn.sh")
    stdin, stdout, stderr = ssh_clients[0].exec_command(
        "rm -rf /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config")
    logger.debug("".join(stdout.readlines()))
    logger.debug("".join(stderr.readlines()))

    stdin, stdout, stderr = ssh_clients[0].exec_command(
        "( cd /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo y | bash ./bmhn.sh )")
    out = stdout.readlines()
    for index, _ in enumerate(out):
        logger.debug(out[index].replace("\n", ""))

    logger.debug("".join(stderr.readlines()))

    logger.info("Getting crypto-config and channel-artifacts from first node...")
    scp_clients[0].get("/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config",
                       f"{config['exp_dir']}/setup", recursive=True)
    scp_clients[0].get("/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts",
                       f"{config['exp_dir']}/setup", recursive=True)

    logger.info("Pushing crypto-config and channel-artifacts to all other nodes")
    for index, _ in enumerate(config['priv_ips']):
        if index != 0:
            stdin, stdout, stderr = ssh_clients[index].exec_command(
                "sudo rm -rf /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts")
            logger.debug("".join(stdout.readlines()))
            logger.debug("".join(stderr.readlines()))
            scp_clients[index].put(f"{config['exp_dir']}/setup/crypto-config",
                                   "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger", recursive=True)
            scp_clients[index].put(f"{config['exp_dir']}/setup/channel-artifacts",
                                   "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger", recursive=True)

            logger.debug(f"Done on node {index}")

    logger.info("Pushing chaincode to all nodes")
    for index, _ in enumerate(config['priv_ips']):
        scp_clients[index].put(f"{dir_name}/chaincode/benchmarking",
                               "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode",
                               recursive=True)

    # Starting Certificate Authorities
    peer_orgs_secret_keys = []
    logger.info(f"Starting Certificate Authorities")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        # get the names of the secret keys for each peer Organizations
        stdin, stdout, stderr = ssh_clients[org - 1].exec_command(
            f"ls -a /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config/peerOrganizations/org{org}.example.com/ca")
        out = stdout.readlines()
        logger.debug(out)
        logger.debug("".join(stderr.readlines()))
        peer_orgs_secret_keys.append(
            "".join(out).replace(f"ca.org{org}.example.com-cert.pem", "").replace("\n", "").replace(" ", "").replace(
                "...", ""))

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
            logger.debug("    --> TLS environment variables set")
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_ENABLED=true"
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_CERTFILE=/etc/hyperledger/fabric-ca-server-config/ca.org{org}.example.com-cert.pem"
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_KEYFILE=/etc/hyperledger/fabric-ca-server-config/{peer_orgs_secret_keys[org - 1]}"
        # else:
        #     string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_ENABLED=false"

        string_ca_v = ""
        string_ca_v = string_ca_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/ca/:/etc/hyperledger/fabric-ca-server-config"

        # Starting the Certificate Authority
        logger.debug(f" - Starting ca for org{org} on {config['pub_ips'][org - 1]}")
        channel = ssh_clients[org - 1].get_transport().open_session()
        channel.exec_command(
            f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_ca_base + string_ca_ca + string_ca_tls + string_ca_v + f" hyperledger/fabric-ca sh -c 'fabric-ca-server start -b admin:adminpw -d' &> /home/ubuntu/ca.org{org}.log)")
        ssh_clients[org - 1].exec_command(
            f"echo \"docker run -it --rm" + string_ca_base + string_ca_ca + string_ca_tls + string_ca_v + " hyperledger/fabric-tools /bin/bash\" >> cli.sh")

    # starting orderer
    logger.info(f"Starting orderers")
    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        # set up configurations of orderers like with docker compose
        string_orderer_base = ""
        string_orderer_base = string_orderer_base + f" --network={my_net} --name orderer{orderer}.example.com -p 7050:7050"
        string_orderer_base = string_orderer_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"
        string_orderer_base = string_orderer_base + f" -e ORDERER_HOME=/var/hyperledger/orderer"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENADDRESS=0.0.0.0"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENPORT=7050"
        string_orderer_base = string_orderer_base + f" -e ODERER_HOST=orderer{orderer}.example.com"
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
            logger.debug("    --> TLS environment variables set")
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ENABLED=true"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_PRIVATEKEY=/var/hyperledger/orderer/tls/server.key"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_CERTIFICATE=/var/hyperledger/orderer/tls/server.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ROOTCAS=[/var/hyperledger/orderer/tls/ca.crt]"
            # string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE=/var/hyperledger/orderer/tls/server.crt"
            # string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY=/var/hyperledger/orderer/tls/server.key"
            # string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_ROOTCAS=[/var/hyperledger/orderer/tls/ca.crt]"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTAUTHREQUIRED=false"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTROOTCAS_FILES=/var/hyperledger/users/Admin@example.com/tls/ca.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTCERT_FILE=/var/hyperledger/users/Admin@example.com/tls/client.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_TLS_CLIENTKEY_FILE=/var/hyperledger/users/Admin@example.com/tls/client.key"
        else:
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ENABLED=false"

        string_orderer_v = ""
        string_orderer_v = string_orderer_v + f" -v $(pwd)/channel-artifacts/genesis.block:/var/hyperledger/orderer/genesis.block"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/msp:/var/hyperledger/orderer/msp"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls:/var/hyperledger/orderer/tls"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/users:/var/hyperledger/users"
        string_orderer_v = string_orderer_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric"

        # Starting the orderers
        logger.debug(f" - Starting orderer{orderer} on {config['pub_ips'][config['fabric_settings']['org_count'] - 1 + orderer]}")
        channel = ssh_clients[config['fabric_settings']['org_count'] + orderer - 1].get_transport().open_session()
        channel.exec_command(
            f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_orderer_base + string_orderer_tls + string_orderer_v + f" hyperledger/fabric-orderer orderer &> /home/ubuntu/orderer{orderer}.log)")
        ssh_clients[config['fabric_settings']['org_count'] + orderer - 1].exec_command(
            f"(cd /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_orderer_base + string_orderer_tls + string_orderer_v + " hyperledger/fabric-tools /bin/bash\" >> /home/ubuntu/cli.sh)")

    # starting peers and databases
    logger.info(f"Starting databases and peers")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        for peer, ip in enumerate(config['pub_ips'][config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (org - 1):
                                  config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * org]):
            # set up configuration of database like with docker compose
            string_database_base = ""
            string_database_base = string_database_base + f" --network='{my_net}' --name couchdb{peer}.org{org} -p 5984:5984"
            string_database_base = string_database_base + f" -e COUCHDB_USER= -e COUCHDB_PASSWORD="
            string_database_base = string_database_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

            # Starting the couchdbs
            logger.debug(f" - Starting database couchdb{peer}.org{org} on {ip}")
            channel = ssh_clients[config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (
                        org - 1) + peer].get_transport().open_session()
            channel.exec_command(
                f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_database_base + f" hyperledger/fabric-couchdb &> /home/ubuntu/couchdb{peer}.org{org}.log)")

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
            string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_STATEDATABASE=CouchDB"
            string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_COUCHDBADDRESS=couchdb{peer}.org{org}:5984"
            # string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_USERNAME="
            # string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_PASSWORD="

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
                logger.debug("    --> TLS environment variables set")
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ENABLED=true"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_CLIENTAUTHREQUIRED=false"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_CERT_FILE=/var/hyperledger/fabric/tls/server.crt"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_KEY_FILE=/var/hyperledger/fabric/tls/server.key"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/fabric/tls/ca.crt"
            else:
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ENABLED=false"

            string_peer_v = ""
            string_peer_v = string_peer_v + f" -v /var/run/:/host/var/run/"
            string_peer_v = string_peer_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/msp:/var/hyperledger/fabric/msp"
            string_peer_v = string_peer_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls:/var/hyperledger/fabric/tls"
            string_peer_v = string_peer_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

            # Starting the peers
            logger.debug(f" - Starting peer{peer}.org{org} on {ip}")
            channel = ssh_clients[config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (org - 1) + peer].get_transport().open_session()
            channel.exec_command(
                f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_peer_base + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + f" hyperledger/fabric-peer peer node start &> /home/ubuntu/peer{peer}.org{org}.log)")
            ssh_clients[
                config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (org - 1) + peer].exec_command(
                f"(cd /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_peer_base + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + " hyperledger/fabric-tools /bin/bash\" >> /home/ubuntu/cli.sh)")

    # Waiting for a few seconds until all has started
    time.sleep(10)
    index_last_node = config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (config['fabric_settings']['org_count'] + 1) - 1
    # Creating script and pushing it to the last node
    logger.debug(
        f"Executing script on {config['pub_ips'][index_last_node]}  which creates channel, adds peers to channel, installs and instantiates all chaincode - can take some minutes")
    write_script(config, logger)
    stdin, stdout, stderr = ssh_clients[index_last_node].exec_command(
        "rm -f /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")
    logger.debug(stdout.readlines())
    logger.debug(stdout.readlines())
    scp_clients[index_last_node].put(f"{config['exp_dir']}/setup/script.sh", "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")

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
        logger.debug("    --> TLS environment variables set")
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ENABLED=true"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_CERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/server.crt"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_KEY_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/server.key"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/ca.crt"
    else:
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ENABLED=false"

    string_cli_v = ""
    string_cli_v = string_cli_v + f" -v /var/run/:/host/var/run/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode/:/opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config:/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts:/opt/gopath/src/github.com/hyperledger/fabric/peer/scripts/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts:/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts"
    string_cli_v = string_cli_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

    # execute script.sh on last node
    stdin, stdout, stderr = ssh_clients[index_last_node].exec_command(
        f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_cli_base + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash -c '(ls -la && cd scripts && ls -la && chmod 777 script.sh && ls -la && cd .. && ./scripts/script.sh)' |& tee /home/ubuntu/setup.log)")
    out = stdout.readlines()
    for index, _ in enumerate(out):
        logger.debug(out[index].replace("\n", ""))

    # save the cli command on the last node and save it in exp_dir
    ssh_clients[index_last_node].exec_command(
        f"(cd /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger && echo \"docker run -it --rm" + string_cli_base + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash\" >> /home/ubuntu/cli2.sh)")

    logger.debug("".join(stderr.readlines()))

    if out[len(out) - 1] == "========= All GOOD, BMHN execution completed =========== \n":
        logger.info("")
        logger.info("**************** !!! Fabric network formation was successful !!! *********************")
        logger.info("")
    else:
        logger.info("")
        logger.info("******************!!! ERROR: Fabric network formation failed !!! *********************")

    logger.info("Getting logs from vms")

    for index, ip in enumerate(config['pub_ips']):
        scp_clients[index].get("/var/log/user_data.log",
                               f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

    try:
        scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs")
        logger.info("Logs fetched successfully")
    except:
        logger.info(f"No logs available on {ip}")

    logger.info("")



def reboot_all(ec2_instances, config, logger, ssh_clients, scp_clients):
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
        for index, ip in enumerate(config['pub_ips']):
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
    logger.debug(f"copying {dir_name}/setup/crypto-config_raw.yaml to {config['exp_dir']}/setup/crypto-config.yaml")

    os.system(
        f"cp {dir_name}/setup/crypto-config_raw.yaml {config['exp_dir']}/setup/crypto-config.yaml")

    os.system(
        f"sed -i -e 's/substitute_orderer_count/{config['fabric_settings']['orderer_count']}/g' {config['exp_dir']}/setup/crypto-config.yaml")

    for org_count in range(1, config['fabric_settings']['org_count'] + 1):
        os.system(f"sed -i -e 's/substitute_peer_count_org{org_count}/{config['fabric_settings']['peer_count']}/g' {config['exp_dir']}/setup/crypto-config.yaml")
        os.system(f"sed -i -e 's/substitute_user_count_org{org_count}/1/g' {config['exp_dir']}/setup/crypto-config.yaml")




def write_configtx(config):
    dir_name = os.path.dirname(os.path.realpath(__file__))

    os.system(
        f"cp {dir_name}/setup/configtx_raw_1.yaml {config['exp_dir']}/setup/configtx.yaml")
    os.system(
        f"cp {dir_name}/setup/configtx_raw_3.yaml {config['exp_dir']}/setup/configtx3.yaml")

    f = open(f"{config['exp_dir']}/setup/configtx2.yaml", "w+")

    if config['fabric_settings']['orderer_type'].upper() == "RAFT":
        f.write("\n    OrdererType: etcdraft\n\n")

        f.write("    EtcdRaft:\n")
        f.write("        Consenters:\n")
        for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
            f.write(f"            - Host: orderer{orderer}.example.com\n")
            f.write(f"              Port: 7050\n")
            f.write(
                f"              ClientTLSCert: crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls/server.crt\n")
            f.write(
                f"              ServerTLSCert: crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls/server.crt\n")


    else:
        f.write("\n    OrdererType: solo\n\n")

    f.write("\n")
    f.write("    Addresses:\n")
    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        f.write(f"        - orderer{orderer}.example.com:7050\n")


    f.close()

    # append the parts of configtx to the final configtx
    os.system(f"cat {config['exp_dir']}/setup/configtx2.yaml >> {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"cat {config['exp_dir']}/setup/configtx3.yaml >> {config['exp_dir']}/setup/configtx.yaml")

    # substitute remaining parameters
    os.system(
        f"sed -i -e 's/substitute_batch_timeout/{config['fabric_settings']['batch_timeout']}/g' {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"sed -i -e 's/substitute_max_message_count/{config['fabric_settings']['max_message_count']}/g' {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"sed -i -e 's/substitute_absolute_max_bytes/{config['fabric_settings']['absolute_max_bytes']}/g' {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"sed -i -e 's/substitute_preferred_max_bytes/{config['fabric_settings']['preferred_max_bytes']}/g' {config['exp_dir']}/setup/configtx.yaml")



def write_script(config, logger):
    dir_name = os.path.dirname(os.path.realpath(__file__))
    os.system(
        f"cp {dir_name}/setup/script_raw_1.sh {config['exp_dir']}/setup/script.sh")

    f = open(f"{config['exp_dir']}/setup/script2.sh", "w+")

    f.write("\n\nsetGlobals() {\n\n")

    f.write("    CORE_PEER_ADDRESS=peer$1.org$2.example.com:7051\n")

    f.write("    CORE_PEER_LOCALMSPID=Org$2MSP\n")

    f.write(
        "    CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/ca.crt\n")
    f.write(
        "    CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/users/Admin@org$2.example.com/msp\n")

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

    os.system(
        f"cp {dir_name}/setup/script_raw_3.sh {config['exp_dir']}/setup/script3.sh")
    if config['fabric_settings']['tls_enabled'] == 1:
        logger.debug("    --> TLS environment variables set")
        string_tls = f"--tls --cafile /opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem"
    else:
        string_tls = f""

    # append the parts of script to the final script
    os.system(f"cat {config['exp_dir']}/setup/script2.sh >> {config['exp_dir']}/setup/script.sh")
    os.system(f"cat {config['exp_dir']}/setup/script3.sh >> {config['exp_dir']}/setup/script.sh")

    # substitute the enumeration of peers
    enum_peers = "0"
    for peer in range(1, config['fabric_settings']['peer_count']):
        enum_peers = enum_peers + f" {peer}"

    endorsement = config['fabric_settings']['endorsement_policy']

    os.system(f"sed -i -e 's/substitute_enum_peers/{enum_peers}/g' {config['exp_dir']}/setup/script.sh")
    os.system(f"sed -i -e 's#substitute_tls#{string_tls}#g' {config['exp_dir']}/setup/script.sh")
    os.system(f"sed -i -e 's/substitute_endorsement/{endorsement}/g' {config['exp_dir']}/setup/script.sh")
