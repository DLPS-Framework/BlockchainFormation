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

    for index, _ in enumerate(config['pub_ips']):
        scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs")
        scp_clients[index].get("/var/log/user_data.log",
                               f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")


def fabric_startup(ec2_instances, config, logger, ssh_clients, scp_clients):
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

    for index, _ in enumerate(config['pub_ips']):

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
    if len(out) == len(config['pub_ips']) + 1:
        logger.info("Docker swarm started successfully")
    else:
        logger.info("Docker swarm setup was not successful")
        sys.exit("Fatal error when performing docker swarm setup")

    logger.info("Creating crypto-config.yaml and pushing it to first node")
    write_crypto_config(config)

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
        f"cp blockchain_specifics/Fabric/setup/bmhn.sh {config['exp_dir']}/setup/bmhn.sh")
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
    for index, _ in enumerate(config['pub_ips']):
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
    for index, _ in enumerate(config['pub_ips']):
        scp_clients[index].put("blockchain_specifics/Fabric/chaincode/benchmarking",
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
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_SERVER_CA_NAME=ca.example.com"
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_SERVER_CA_CERTFILE=/etc/hyperledger/fabric-ca-server-config/ca.org{org}.example.com-cert.pem"
        string_ca_ca = string_ca_ca + f" -e FABRIC_CA_SERVER_CA_KEYFILE=/etc/hyperledger/fabric-ca-server-config/{peer_orgs_secret_keys[org - 1]}"

        string_ca_tls = ""
        if config['fabric_settings']['tls_enabled'] == 1:
            logger.debug("    --> TLS environment variables set")
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_ENABLED=true"
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_CERTFILE=/etc/hyperledger/fabric-ca-server-config/ca.org{org}.example.com-cert.pem"
            string_ca_tls = string_ca_tls + f" -e FABRIC_CA_SERVER_TLS_KEYFILE=/etc/hyperledger/fabric-ca-server-config/{peer_orgs_secret_keys[org - 1]}"

        string_ca_v = ""
        string_ca_v = string_ca_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/ca/:/etc/hyperledger/fabric-ca-server-config"

        # Starting the Certificate Authority
        logger.debug(f" - Starting ca for org{org} on {config['pub_ips'][org - 1]}")
        channel = ssh_clients[org - 1].get_transport().open_session()
        channel.exec_command(
            f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_ca_base + string_ca_ca + string_ca_tls + string_ca_v + f" hyperledger/fabric-ca sh -c 'fabric-ca-server start -b admin:adminpw -d' &> /home/ubuntu/ca.org{org}.log)")
        ssh_clients[org - 1].exec_command(
            f"echo \"docker run -it --rm" + string_ca_v + " hyperledger/fabric-tools /bin/bash\" >> cli.sh")

    # starting orderer
    logger.info(f"Starting orderers")
    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        # set up configurations of orderers like with docker compose
        string_orderer_base = ""
        string_orderer_base = string_orderer_base + f" --network={my_net} --name orderer{orderer}.example.com -p 7050:7050"
        string_orderer_base = string_orderer_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"
        # string_orderer_base = string_orderer_base + f" -e ORDERER_HOME=/var/hyperledger/orderer"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENADDRESS=0.0.0.0"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LISTENPORT=7050"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_GENESISMETHOD=file"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_GENESISFILE=/var/hyperledger/orderer/genesis.block"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LOCALMSPID=OrdererMSP"
        string_orderer_base = string_orderer_base + f" -e ORDERER_GENERAL_LOCALMSPDIR=/var/hyperledger/orderer/msp"
        string_orderer_base = string_orderer_base + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

        string_orderer_tls = ""
        if config['fabric_settings']['tls_enabled'] == 1:
            logger.debug("    --> TLS environment variables set")
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ENABLED=true"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_PRIVATEKEY=/var/hyperledger/orderer/tls/server.key"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_CERTIFICATE=/var/hyperledger/orderer/tls/server.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_TLS_ROOTCAS=[/var/hyperledger/orderer/tls/ca.crt]"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE=/var/hyperledger/orderer/tls/server.crt"
            string_orderer_tls = string_orderer_tls + f" -e ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY=/var/hyperledger/orderer/tls/server.key"

        string_orderer_v = ""
        string_orderer_v = string_orderer_v + f" -v $(pwd)/channel-artifacts/genesis.block:/var/hyperledger/orderer/genesis.block"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/msp:/var/hyperledger/orderer/msp"
        string_orderer_v = string_orderer_v + f" -v $(pwd)/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls:/var/hyperledger/orderer/tls"
        string_orderer_v = string_orderer_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric"

        # Starting the orderers
        logger.debug(f" - Starting orderer{orderer} on {config['pub_ips'][config['fabric_settings']['org_count'] - 1 + orderer]}")
        channel = ssh_clients[config['fabric_settings']['org_count'] + orderer - 1].get_transport().open_session()
        channel.exec_command(
            f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_orderer_base + string_orderer_tls + string_orderer_v + f" hyperledger/fabric-orderer orderer &> /home/ubuntu/orderer{orderer}.log)")
        ssh_clients[config['fabric_settings']['org_count'] + orderer - 1].exec_command(
            f"echo \"docker run -it --rm" + string_orderer_v + " hyperledger/fabric-tools /bin/bash\" >> cli.sh")

    link_string = ""
    # starting peers and databases
    logger.info(f"Starting databases and peers")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        for peer, ip in enumerate(config['pub_ips'][
                                  config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (org - 1):
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

            for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
                link_string = link_string + f" --link orderer{orderer}.example.com:orderer{orderer}.example.com"

            for peer_org2 in range(1, org + 1):
                if peer_org2 < org:
                    end = config['fabric_settings']['org_count']
                else:
                    end = peer

                for peer2 in range(0, end + 1):
                    link_string = link_string + f" --link peer{peer2}.org{peer_org2}.example.com:peer{peer2}.org{org}.example.com"

            string_peer_base = ""
            string_peer_base = string_peer_base + f" --network='{my_net}' --name peer{peer}.org{org}.example.com -p 7051:7051 -p 7053:7053"

            string_peer_link = link_string

            string_peer_database = ""
            string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_STATEDATABASE=CouchDB"
            string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_COUCHDBADDRESS=couchdb{peer}.org{org}:5984"
            string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_USERNAME="
            string_peer_database = string_peer_database + f" -e CORE_LEDGER_STATE_COUCHDBCONFIG_PASSWORD="

            string_peer_core = ""
            string_peer_core = string_peer_core + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"
            string_peer_core = string_peer_core + f" -e CORE_LOGGING_MSP={config['fabric_settings']['log_level']}"
            string_peer_core = string_peer_core + f" -e CORE_PEER_ADDRESSAUTODETECT=true"
            string_peer_core = string_peer_core + f" -e CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock"
            string_peer_core = string_peer_core + f" -e CORE_PEER_NETWORKID=peer{peer}.org{org}.example.com"
            string_peer_core = string_peer_core + f" -e CORE_NEXT=true"
            string_peer_core = string_peer_core + f" -e CORE_PEER_ENDORSER_ENABLED=true"
            string_peer_core = string_peer_core + f" -e CORE_PEER_ID=peer{peer}.org{org}.example.com"
            string_peer_core = string_peer_core + f" -e CORE_PEER_PROFILE_ENABLED=true "
            string_peer_core = string_peer_core + f" -e CORE_PEER_COMMITTER_LEDGER_ORDERER=orderer1.example.com:7050"
            string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_IGNORESECURITY=true"
            string_peer_core = string_peer_core + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"
            string_peer_core = string_peer_core + f" -e CORE_PEER_LOCALMSPID=Org{org}MSP"
            string_peer_core = string_peer_core + f" -e CORE_PEER_MSPCONFIGPATH=/var/hyperledger/fabric/msp"
            string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_EXTERNALENDPOINT=peer{peer}.org{org}.example.com:7051"
            string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_USELEADERELECTION=false"
            string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_ORGLEADER=true"
            if peer != 0:
                string_peer_core = string_peer_core + f" -e CORE_PEER_GOSSIP_BOOTSTRAP=peer0.org{org}.example.com:7051"

            string_peer_tls = ""
            if config['fabric_settings']['tls_enabled'] == 1:
                logger.debug("    --> TLS environment variables set")
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ENABLED=true"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_CLIENTAUTHREQUIRED=false"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_CERT_FILE=/var/hyperledger/fabric/tls/server.crt"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_KEY_FILE=/var/hyperledger/fabric/tls/server.key"
                string_peer_tls = string_peer_tls + f" -e CORE_PEER_TLS_ROOTCERT_FILE=/var/hyperledger/fabric/tls/ca.crt"

            string_peer_v = ""
            string_peer_v = string_peer_v + f" -v /var/run/:/host/var/run/"
            string_peer_v = string_peer_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/msp:/var/hyperledger/fabric/msp"
            string_peer_v = string_peer_v + f" -v $(pwd)/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls:/var/hyperledger/fabric/tls"
            string_peer_v = string_peer_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

            # Starting the peers
            logger.debug(f" - Starting peer{peer}.org{org} on {ip}")
            channel = ssh_clients[config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (
                        org - 1) + peer].get_transport().open_session()
            channel.exec_command(
                f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_peer_base + string_peer_link + string_peer_database + string_peer_core + string_peer_tls + string_peer_v + f" hyperledger/fabric-peer peer node start &> /home/ubuntu/peer{peer}.org{org}.log)")
            ssh_clients[
                config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (org - 1) + peer].exec_command(
                f"echo \"docker run -it --rm" + string_peer_v + " hyperledger/fabric-tools /bin/bash\" >> cli.sh")

    # Waiting for a few seconds until all has started
    time.sleep(10)

    # Creating script and pushing it to the last node
    logger.debug(
        "Executing script on last node which creates channel, adds peers to channel, installs and instantiates all chaincode - can take some minutes")
    write_script(config, logger)
    stdin, stdout, stderr = ssh_clients[config["vm_count"] - 1].exec_command(
        "rm -f /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")
    logger.debug(stdout.readlines())
    logger.debug(stdout.readlines())
    scp_clients[config["vm_count"] - 1].put(f"{config['exp_dir']}/setup/script.sh",
                                            "/home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts/script.sh")

    # Setting up configuration of cli like with docker compose
    string_cli_base = ""
    string_cli_base = string_cli_base + f" --network='{my_net}' --name cli -p 12051:7051 -p 12053:7053"
    string_cli_base = string_cli_base + f" -e GOPATH=/opt/gopath"
    string_cli_base = string_cli_base + f" -e FABRIC_LOGGING_SPEC={config['fabric_settings']['log_level']}"

    string_cli_link = link_string
    string_cli_link = string_cli_link + f" --link peer{peer}.org{org}.example.com:peer{peer}.org{org}.example.com"

    string_cli_core = ""
    string_cli_core = string_cli_core + f" -e CORE_PEER_LOCALMSPID=Org{org}MSP"
    string_cli_core = string_cli_core + f" -e CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock"
    string_cli_core = string_cli_core + f" -e CORE_PEER_ID=cli"
    string_cli_core = string_cli_core + f" -e CORE_PEER_ADDRESS=peer0.org{org}.example.com:7051"
    string_cli_core = string_cli_core + f" -e CORE_PEER_NETWORKID=cli"
    string_cli_core = string_cli_core + f" -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/users/Admin@org{org}.example.com/msp"
    string_cli_core = string_cli_core + f" -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net}"

    string_cli_tls = ""
    if config['fabric_settings']['tls_enabled'] == 1:
        logger.debug("    --> TLS environment variables set")
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ENABLED=true"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_CERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/server.crt"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_KEY_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/server.key"
        string_cli_tls = string_cli_tls + f" -e CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org{org}.example.com/peers/peer{peer}.org{org}.example.com/tls/ca.crt"

    string_cli_v = ""
    string_cli_v = string_cli_v + f" -v /var/run/:/host/var/run/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/chaincode/:/opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/crypto-config:/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/scripts:/opt/gopath/src/github.com/hyperledger/fabric/peer/scripts/"
    string_cli_v = string_cli_v + f" -v /home/ubuntu/fabric-samples/Build-Multi-Host-Network-Hyperledger/channel-artifacts:/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts"
    string_cli_v = string_cli_v + f" -w /opt/gopath/src/github.com/hyperledger/fabric/peer"

    # execute script.sh on last node
    stdin, stdout, stderr = ssh_clients[config["vm_count"] - 1].exec_command(
        f"(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && docker run --rm" + string_cli_base + string_cli_link + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash -c './scripts/script.sh' |& tee /home/ubuntu/setup.log)")
    out = stdout.readlines()
    for index, _ in enumerate(out):
        logger.debug(out[index].replace("\n", ""))

    # save the cli command on the last node and save it in exp_dir
    ssh_clients[config['vm_count'] - 1].exec_command(
        f"echo \"docker run -it --rm" + string_cli_base + string_cli_link + string_cli_core + string_cli_tls + string_cli_v + f" hyperledger/fabric-tools /bin/bash\" >> cli2.sh")
    scp_clients[config['vm_count'] - 1].get(f"/home/ubuntu/cli.sh",
                                            f"{config['exp_dir']}/setup")

    logger.debug("".join(stderr.readlines()))

    if out[len(out) - 1] == "========= All GOOD, BMHN execution completed =========== \n":
        logger.info("")
        logger.info("********************* !!! Successful !!! *********************")
        logger.info("")
    else:
        logger.info("")
        logger.info("********!!! ERROR: Fabric network formation failed !!! ********")

    logger.info("Creating network setup for API stuff")
    logger.debug("Writing raw network.json")
    write_network(config)
    logger.debug("Writing replacement script")
    write_replacement(config)
    logger.debug("Finalizing network.json")
    os.system(f"bash {config['exp_dir']}/api/replacement.sh")
    logger.debug("Copying User-specific credentials")
    os.system(f"mkdir {config['exp_dir']}/api/creds")
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        os.system(f"cp -r {config['exp_dir']}/setup/crypto-config/peerOrganizations/org{org}.example.com/users/User1@org{org}.example.com {config['exp_dir']}/api/creds")

    logger.debug("Setting up wallet")
    os.system(
        f"cp blockchain_specifics/Fabric/api/* {config['exp_dir']}/api")

""" THIS IS CLIENT-STUFF
    # push api-stuff to ca-nodes
    for org in range(1, config['fabric_settings']['org_count'] + 1):
        scp_clients[org - 1].put(f"{config['exp_dir']}/api", "/home/ubuntu",
                                 recursive=True)
        sk_name_user = subprocess.Popen(f"ls {config['exp_dir']}/api/creds/User1@org{org}.example.com/msp/keystore/", shell=True,
                                        stdout=subprocess.PIPE).stdout.readlines()[0].decode("utf8").replace("\n", "")
        stdin, stdout, stderr = ssh_clients[org - 1].exec_command(
            f"sed -i -e 's/sk_name_user/{sk_name_user}/g' /home/ubuntu/api/addToWallet_raw.js && sed -i -e 's/id_name_user/User1@org{org}.example.com/g' /home/ubuntu/api/addToWallet_raw.js && sed -i -e 's/id_name_msp/Org{org}MSP.example.com/g' /home/ubuntu/api/addToWallet_raw.js && sed -i -e 's/user_name/User1@org{org}.example.com/g' /home/ubuntu/api/benchmarking.js")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[org - 1].exec_command(
            f"mv /home/ubuntu/api/addToWallet_raw.js /home/ubuntu/api/addToWallet.js")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())
        stdin, stdout, stderr = ssh_clients[org - 1].exec_command(
            "cd /home/ubuntu/api && bash ./script.sh &> install.log")
        logger.debug(stdout.readlines())
        logger.debug(stderr.readlines())

    for org in range(1, config['fabric_settings']['org_count'] + 1):
        channel = ssh_clients[org - 1].get_transport().open_session()
        channel.exec_command(
            "source /home/ubuntu/.profile && cd /home/ubuntu/api && node benchmarking.js >> benchmarking.log")

    for index, ip in enumerate(config['pub_ips']):
        scp_clients[index].get("/var/log/user_data.log",
                               f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")
        try:
            scp_clients[index].get("/home/ubuntu/*.log", f"{config['exp_dir']}/fabric_logs")
            scp_clients[index].get("")
        except:
            logger.info("No logs available on {ip}")

    # set environment variables on last node
    # string_env = 'CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp; CORE_PEER_LOCALMSPID="Org1MSP"; CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt; CORE_PEER_ADDRESS=peer0.org1.example.com:7051; HALLO=nope'
    # string_cc = 'peer chaincode instantiate -o orderer.example.com:7050 -C mychannel -n mycc -v 1.0 -c \'{"Args":["init","a","100","b","200"]}\' -P "OR (\'Org1MSP.member\',\'Org2MSP.member\')"'
    # stdin, stdout, stderr = ssh_clients[index].exec_command(string_cli + " -c '" + string_env + "; " + string_cc + "')")
    # logger.debug("".join(stdout.readlines()))
    # logger.debug("".join(stderr.readlines()))

    # string_cc = 'peer chaincode instantiate -o orderer.example.com:7050 -C mychannel -n mycc -v 1.0 -c \'{"Args":["init","a","100","b","200"]}\' -P "OR (\'Org1MSP.member\',\'Org2MSP.member\')'
    # stdin, stdout, stderr = ssh_clients[index].exec_command(string_cli + " -c '" + string_cc + "')")
    # logger.debug("".join(stdout.readlines()))
    # logger.debug("".join(stderr.readlines()))

    # on the ith node, access couchDB with
    # string_couchDB = f"http://{config['pub_ips'][0]}:5984/_utils/#database/mychannel_/_all_docs"
    # string_cli_it = "(cd ~/fabric-samples/Build-Multi-Host-Network-Hyperledger && " + f"docker run -it --rm --network='{my_net}' --name cli --link orderer.example.com:orderer.example.com" + link_string + f" -p 12051:7051 -p 12053:7053 -e GOPATH=/opt/gopath -e CORE_PEER_LOCALMSPID=Org1MSP -e CORE_PEER_TLS_ENABLED=false -e CORE_VM_ENDPOINT=unix:///host/var/run/docker.sock -e CORE_PEER_ID=cli -e CORE_PEER_ADDRESS=peer0.org1.example.com:7051 -e CORE_PEER_NETWORKID=cli -e CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp -e CORE_VM_DOCKER_HOSTCONFIG_NETWORKMODE={my_net} -v /var/run/:/host/var/run/ -v $(pwd)/chaincode/:/opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/go -v $(pwd)/crypto-config:/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/ -v $(pwd)/scripts:/opt/gopath/src/github.com/hyperledger/fabric/peer/scripts/ -v $(pwd)/channel-artifacts:/opt/gopath/src/github.com/hyperledger/fabric/peer/channel-artifacts -w /opt/gopath/src/github.com/hyperledger/fabric/peer hyperledger/fabric-tools /bin/bash)"
    # logger.info("# on every node, start cli with " + string_cli_it)
    # put environment with <<< CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp; CORE_PEER_LOCALMSPID="Org1MSP"; CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt; CORE_PEER_ADDRESS=peer1.org1.example.com:7051 >>>
    # instantiate cc on any node with <<< peer chaincode instantiate -o orderer.example.com:7050 -C mychannel -n mycc -v 1.0 -c '{"Args":["init","a","100","b","200"]}' -P "OR ('Org1MSP.member','Org2MSP.member')" >>>
    # invoke cc on any node with <<< peer chaincode invoke -o orderer.example.com:7050 -C mychannel -n mycc -c '{"Args":["invoke","a","b","10"]}' >>>
    # query cc on any node with <<< peer chaincode query -C mychannel -n mycc -c '{"Args":["query","a"]}' >>>
"""

    # logger.info("\n !!! Network started successfully !!! \n")


def reboot_all(ec2_instances, config, logger, ssh_clients, scp_clients):
    status_flags = np.zeros((config['vm_count']), dtype=bool)
    timer = 4
    logger.info("   ###              ***               ###")
    logger.info("               Rebooting all VMs      ###")
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


def write_configtx(config):
    os.system(
        f"cp blockchain_specifics/Fabric/setup/configtx_raw_1.yaml {config['exp_dir']}/setup/configtx.yaml")
    os.system(
        f"cp blockchain_specifics/Fabric/setup/configtx_raw_3.yaml {config['exp_dir']}/setup/configtx3.yaml")

    f = open(f"{config['exp_dir']}/setup/configtx2.yaml", "w+")

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
        f"sed -i -e 's/substitute_batch_timeout/{config['batch_timeout']}/g' {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"sed -i -e 's/substitute_max_message_count/{config['fabric_settings']['max_message_count']}/g' {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"sed -i -e 's/substitute_absolute_max_bytes/{config['fabric_settings']['absolute_max_bytes']}/g' {config['exp_dir']}/setup/configtx.yaml")
    os.system(f"sed -i -e 's/substitute_preferred_max_bytes/{config['fabric_settings']['preferred_max_bytes']}/g' {config['exp_dir']}/setup/configtx.yaml")


def write_crypto_config(config):
    os.system(
        f"cp blockchain_specifics/Fabric/setup/crypto-config_raw.yaml {config['exp_dir']}/setup/crypto-config.yaml")

    os.system(
        f"sed -i -e 's/substitute_orderer_count/{config['fabric_settings']['orderer_count']}/g' {config['exp_dir']}/setup/crypto-config.yaml")

    for org_count in range(1, config['fabric_settings']['org_count'] + 1):
        os.system(f"sed -i -e 's/substitute_peer_count_org{org_count}/{config['fabric_settings']['peer_count']}/g' {config['exp_dir']}/setup/crypto-config.yaml")
        os.system(f"sed -i -e 's/substitute_user_count_org{org_count}/1/g' {config['exp_dir']}/setup/crypto-config.yaml")


def write_script(config, logger):
    os.system(
        f"cp blockchain_specifics/Fabric/setup/script_raw_1.sh {config['exp_dir']}/setup/script.sh")

    f = open(f"{config['exp_dir']}/setup/script2.sh", "w+")

    f.write("\n\nsetGlobals() {\n\n")

    f.write("    CORE_PEER_LOCALMSPID=\"Org\"$2\"MSP\"\n")
    f.write(
        "    CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer0.org$2.example.com/tls/ca.crt\n")
    f.write(
        "    CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/users/Admin@org$2.example.com/msp\n")

    if config['fabric_settings']['peer_count'] == 1:
        f.write("    CORE_PEER_ADDRESS=peer0.org$2.example.com:7051\n")
    else:
        f.write("    if [ $1 -eq 0 ]; then\n        CORE_PEER_ADDRESS=peer0.org$2.example.com:7051\n")
        for peer in range(1, config['fabric_settings']['peer_count']):
            f.write(f"    elif [ $1 -eq {peer} ]; then\n")
            f.write(f"        CORE_PEER_ADDRESS=peer$1.org$2.example.com:7051\n")
            f.write(
                f"        CORE_PEER_MSPCONFIGPATH=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/users/Admin@org$2.example.com/msp\n")

            if config['fabric_settings']['tls_enabled'] == 1:
                f.write("        # setting TLS environment variables")
                f.write(f"        CORE_PEER_TLS_ENABLED=true\n")
                f.write(f"        CORE_PEER_TLS_CLIENTAUTHREQUIRED=false\n")
                f.write(
                    f"        CORE_PEER_TLS_CERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/server.crt\n")
                f.write(
                    f"        CORE_PEER_TLS_KEY_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/server.key\n")
                f.write(
                    f"        CORE_PEER_TLS_ROOTCERT_FILE=/opt/gopath/src/github.com/hyperledger/fabric/peer/crypto-config/peerOrganizations/org$2.example.com/peers/peer$1.org$2.example.com/tls/ca.crt\n")
            else:
                f.write(f"        CORE_PEER_TLS_ENABLED=false\n")

    f.write("    fi\n")
    f.write("}\n\n")

    f.close()

    os.system(
        f"cp blockchain_specifics/Fabric/setup/script_raw_3.sh {config['exp_dir']}/setup/script3.sh")
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


def write_network(config):
    with open(f"{config['exp_dir']}/api/network.json", "w+") as file:
        network = {}
        network["name"] = "my-net"
        network["x-type"] = "hlfv1"
        network["version"] = "1.0.0"
        network["channels"] = {
            "mychannel": {
                "orderers": [],
                "peers": {}
            }
        }
        network["organizations"] = {
            "Org1": {
                "mspid": "Org1MSP",
                "peers": [],
                "certificateAuthorities": [
                    "ca_org1"
                ]
            },
            "Org2": {
                "mspid": "Org2MSP",
                "peers": [],
                "certificateAuthorities": [
                    "ca_org2"
                ]
            }
        }
        network["orderers"] = {}
        network["peers"] = {}
        network["certificateAuthorities"] = {
            "ca_org1": {
                "url": f"https://{config['pub_ips'][0]}:7054",
                "name": "ca_org1",
                "httpOptions": {
                    "verify": False
                }
            },
            "ca_org2": {
                "url": f"https://{config['pub_ips'][1]}:7054",
                "name": "ca_org2",
                "httpOptions": {
                    "verify": False
                }
            }
        }

        for org in range(1, config['fabric_settings']['org_count'] + 1):
            for peer, ip in enumerate(config['pub_ips'][
                                      config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * (org - 1):
                                      config['fabric_settings']['org_count'] + config['fabric_settings']['orderer_count'] + config['fabric_settings']['peer_count'] * org]):
                network["channels"]["mychannel"]["peers"][f"peer{peer}.org{org}.example.com"] = {
                    "endorsingPeer": True,
                    "chaincodeQuery": True,
                    "eventSource": True
                }

                network["organizations"][f"Org{org}"]["peers"].append(f"peer{peer}.org{org}.example.com")

                network["peers"][f"peer{peer}.org{org}.example.com"] = {
                    "url": f"grpcs://{ip}:7051",
                    "grpcOptions": {
                        "ssl-target-override": f"peer{peer}.org{org}.example.com"
                    },
                    "tlsCACerts": {
                        "pem": f"INSERT_ORG{org}_CA_CERT"
                    }
                }

        for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
            ip = config['pub_ips'][config['fabric_settings']['org_count'] + orderer - 1]

            network["channels"]["mychannel"]["orderers"].append(f"orderer{orderer}.example.com")

            network["orderers"][f"orderer{orderer}.example.com"] = {
                "url": f"grpcs://{ip}:7050",
                "grpcOptions": {
                    "ssl-target-name-override": f"orderer{orderer}.example.com"
                },
                "tlsCACerts": {
                    "pem": f"INSERT_ORDERER{orderer}_CA_CERT"
                }
            }

        json.dump(network, file, indent=4)


def write_replacement(config):
    f = open(f"{config['exp_dir']}/api/replacement.sh", "w+")

    f.write("#!/bin/bash\n\n")

    f.write("NETWORK=$1\nVERSION=$2\n\n")

    for peer_org in range(1, config['fabric_settings']['org_count'] + 1):
        f.write(
            f"ORG{peer_org}" + """_CERT=$(awk 'NF {sub(/\\r/, ""); printf "%s\\\\\\\\n",$0;}'""" + f" {config['exp_dir']}/setup/crypto-config/peerOrganizations/org{peer_org}.example.com/peers/peer0.org{peer_org}.example.com/tls/ca.crt )\n")

    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        f.write(
            f"ORDERER_CERT{orderer}" + """=$(awk 'NF {sub(/\\r/, ""); printf "%s\\\\\\\\n",$0;}'""" + f" {config['exp_dir']}/setup/crypto-config/ordererOrganizations/example.com/orderers/orderer{orderer}.example.com/tls/ca.crt )\n")
        f.write("\n")

    f.write("\n\n\n")

    for peer_org in range(1, config['fabric_settings']['org_count'] + 1):
        f.write(
            f'sed -i "s~INSERT_ORG{peer_org}_CA_CERT~$ORG{peer_org}_CERT~g"' + f" {config['exp_dir']}/api/network.json\n")

    for orderer in range(1, config['fabric_settings']['orderer_count'] + 1):
        f.write(
            f'sed -i "s~INSERT_ORDERER{orderer}_CA_CERT~$ORDERER_CERT{orderer}~g"' + f" {config['exp_dir']}/api/network.json\n")

    f.close()