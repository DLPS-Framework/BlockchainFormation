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


from BlockchainFormation.utils.utils import *

import hashlib


def indy_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the indy specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['priv_ips']):

        logger.info("Killing all indy processes")

        stdin, stdout, stderr = ssh_clients[index].exec_command("screen -list | grep Detached | cut -d. -f1 | awk '{print $1}' | xargs kill")
        wait_and_log(stdout, stderr)

        time.sleep(5)

        logger.debug("Deleting ledger and wallet data")

        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo rm -r /home/ubuntu/.indy_client /data/indy /var/log/indy")
        wait_and_log(stdout, stderr)

        stdin, stdout, stderr = ssh_clients[index].exec_command("sudo mkdir /var/log/indy /data/indy /data/indy/backup /data/indy/plugins; sudo chown -R ubuntu:ubuntu /var/log/indy/ /data/indy/ /etc/indy/")
        wait_and_log(stdout, stderr)


def indy_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the indy specific startup script
    :return:
    """

    for index, _ in enumerate(config['priv_ips']):
        scp_clients[index].get("/var/log/user_data.log", f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

    # the indices of the blockchain nodes
    config['node_indices'] = list(range(0, config['vm_count']))

    node_names = []
    node_seeds = []
    ips_string = ""
    node_nums = ""

    for node, _ in enumerate(config['priv_ips']):
        node_names.append(f"Node{node+1}")
        node_name = hashlib.md5(node_names[node].encode()).hexdigest()
        node_seeds.append(node_name)
        if ips_string != "":
            ips_string = ips_string + ","
        ips_string = ips_string + config['priv_ips'][node]

        if node_nums != "":
            node_nums = node_nums + " "
        node_nums = node_nums + f"{node+1}"

    port = 9700
    channels = []

    for node, _ in enumerate(config['priv_ips']):
        init_string = f"init_indy_keys --name {node_names[node]} --seed {node_seeds[node]}"
        stdin, stdout, stderr = ssh_clients[node].exec_command(f"{init_string} && echo \"{init_string}\" >> commands.txt")
        wait_and_log(stdout, stderr)
        tx_string = f"generate_indy_pool_transactions --nodes {len(ssh_clients)} --clients {config['indy_settings']['clients']} --nodeNum {node+1} --ips \'{ips_string}\' --network my-net"
        stdin, stdout, stderr = ssh_clients[node].exec_command(f"{tx_string} && echo \"{tx_string}\" >> commands.txt")
        wait_and_log(stdout, stderr)
        channel = ssh_clients[node].get_transport().open_session()
        channels.append(channel)
        start_string = f"screen -dmS indy-node start_indy_node {node_names[node]} 0.0.0.0 {port+1} 0.0.0.0 {port+2} -vv"
        channels[node].exec_command(f"{start_string} && echo \"{start_string}\" >> commands.txt")
        port = port + 2
        time.sleep(5)

    logger.info("Indy network is running...")
    # indy-cli
    # pool create my-pool gen_txn_file=/data/indy/my-net/pool_transactions_genesis

    # VERY HELPFUL:
    # in indy-sdk/samples/python/getting_started.py change src.utils to utils
    # in indy-sdk/samples/python/utils.py change pool_ip return value to 0.0.0.0 and pool_genesis_transactions_file to /data/indy/my-net/pool_transactions_genesis


def indy_restart(config, logger, ssh_clients, scp_clients):

    indy_shutdown(config, logger, ssh_clients, scp_clients)
    indy_startup(config, logger, ssh_clients, scp_clients)
