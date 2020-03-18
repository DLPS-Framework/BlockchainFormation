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


class Couchdb:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the CouchDB specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        logger.info("Shutting down the CouchDB instance")

        try:
            stdin, stdout, stderr = ssh_clients[0].exec_command("docker kill mycouch && rm -r /data/CouchDB_database_dir && mkdir /data/CouchDB_database_dir")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            logger.info("Checking whether everything is shut down cleanly")
            stdin, stdout, stderr = ssh_clients[0].exec_command("docker ps && docker image ls")
            out = stdout.readlines()

            logger.debug(out)
            logger.debug(stderr.readlines())

            if len(out) != 2:
                logger.info("Killing the CouchDB docker instance failed")
                raise Exception("Something seems to be running still")

        except Exception as e:

            channel = ssh_clients[0].get_transport().open_session()
            channel.exec_command("sudo reboot")

            # Wait because the following check for instance state is too soon otherwise
            time.sleep(10)

            # Wait until user Data is finished
            if False in wait_till_done(config, ssh_clients, config['ips'], 30 * 60, 60, "/var/log/user_data_success.log", False, 10 * 60, logger):
                logger.error('CouchDB shutdown not successful')
                raise Exception("Restart failed")

        logger.info("")
        logger.info("**************** !!! CouchDB shutdown was successful !!! *********************")
        logger.info("")

    @staticmethod
    def startup(node_handler):
        """
        Runs the CouchDB specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        dir_name = os.path.dirname(os.path.realpath(__file__))

        # the indices of the blockchain nodes
        config['node_indices'] = list(range(0, config['vm_count']))
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

        stdin, stdout, stderr = ssh_clients[0].exec_command("mkdir /data/CouchDB_database_dir && mkdir /home/ubuntu/couchdb && mkdir /home/ubuntu/couchdb/etc")
        wait_and_log(stdout, stderr)
        scp_clients[0].put(f"{dir_name}/setup", "/home/ubuntu/couchdb/etc", recursive=True)

        Couchdb.start_docker(config, logger, ssh_clients)

    @staticmethod
    def start_docker(config, logger, ssh_clients):
        """
        Starts the CouchDB docker container
        :param config:
        :param logger:
        :param ssh_clients:
        """
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("docker run --rm --name mycouch -p 5984:5984 -e COUCHDB_USER= -e COUCHDB_PASSWORD= -v /data:/opt/couchdb/data -v /home/ubuntu/couchdb/etc:/opt/couchdb/etc/local.d couchdb")

        time.sleep(60)

        logger.info("Checking whether the docker container has started")
        stdin, stdout, stderr = ssh_clients[0].exec_command("docker ps")
        wait_and_log(stdout, stderr)

        logger.info("Testing a request on the CouchDB REST API locallly")
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"curl http://{config['priv_ips'][0]}:5984")
        wait_and_log(stdout, stderr)

        logger.info("")
        logger.info("**************** !!! CouchDB setup was successful !!! *********************")
        logger.info("")

    @staticmethod
    def restart(node_handler):
        """
        Restarts the CouchDB
        :param config:
        :param logger:
        :param ssh_clients:
        :param scp_clients:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        Couchdb.shutdown(config, logger, ssh_clients, scp_clients)
        Couchdb.start_docker(config, logger, ssh_clients)
