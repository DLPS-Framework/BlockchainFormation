#  Copyright 2019  Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
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

import glob
import itertools
import json
import os
import re
import time
import numpy as np
import urllib3
from web3 import Web3
import web3
from web3.middleware import geth_poa_middleware

#TODO: Make code more efficient and nicer
#TODO: improve natural sorting stuff


########## U G L Y  M O N K E Y P A T C H ##################
# web3 does not support request retry function, therefore we inject it ourselves
# https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests/47475019#47475019
import lru
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from web3._utils.caching import (
    generate_cache_key,
)


def _remove_session(key, session):
    session.close()

_session_cache = lru.LRU(8, callback=_remove_session)

def _get_session_new(*args, **kwargs):
    cache_key = generate_cache_key((args, kwargs))
    if cache_key not in _session_cache:
        _session_cache[cache_key] = requests.Session()
        #TODO: Adjust these parameters
        retry = Retry(connect=10, backoff_factor=0.3)
        adapter = HTTPAdapter(max_retries=retry)
        _session_cache[cache_key].mount('http://', adapter)
        _session_cache[cache_key].mount('https://', adapter)
    return _session_cache[cache_key]

web3._utils.request._get_session = _get_session_new

#############################################


def geth_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the geth specific shutdown operations (e.g. pulling the geth logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['ips']):
        # get account from all instances
        try:
            scp_clients[index].get("/var/log/geth.log",
                                   f"{config['exp_dir']}/geth_logs/geth_log_node_{index}.log")
            scp_clients[index].get("/var/log/user_data.log",
                                   f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

        except:
            logger.info("Geth logs could not be pulled from the machines.")


def geth_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """

    # the indices of the blockchain nodes
    config['node_indices'] = list(range(0, config['vm_count']))

    #acc_path = os.getcwd()
    os.mkdir(f"{config['exp_dir']}/setup/accounts")
    # enodes dir not needed anymore since enodes are saved in static-nodes file
    # os.mkdir((f"{path}/{self.config['exp_dir']}/enodes"))
    os.mkdir(f"{config['exp_dir']}/geth_logs")

    for index, _ in enumerate(config['ips']):
        scp_clients[index].get("/data/gethNetwork/account.txt",
                               f"{config['exp_dir']}/setup/accounts/account_node_{index}.txt")
        scp_clients[index].get("/data/keystore",
                               f"{config['exp_dir']}/setup/accounts/keystore_node_{index}", recursive=True)
    all_accounts = []

    acc_path = f"{config['exp_dir']}/setup/accounts"
    file_list = os.listdir(acc_path)
    # Sorting to get matching accounts to ip
    file_list.sort(key=natural_keys)
    for file in file_list:
        try:
            file = open(os.path.join(acc_path + "/" + file), 'r')
            all_accounts.append(file.read())
            file.close()
        except IsADirectoryError:
            logger.debug(f"{file} is a directory")

    all_accounts = [x.rstrip() for x in all_accounts]
    logger.info(all_accounts)

    # which node gets which account unlocked
    account_mapping = get_relevant_account_mapping(all_accounts, config)

    # https://github.com/ethereum/go-ethereum/wiki/Command-Line-Options
    # Put all performance setting from config into one string to make service creation in the following lines more lean
    # FIXME --trie-cache-gens {config['geth_settings']['trie-cache-gens']}  trie-cache-gens not available but it is listed in docs
    performance_settings = f"--cache {config['geth_settings']['cache']} --cache.database {config['geth_settings']['cache.database']} " \
        f"--cache.gc {config['geth_settings']['cache.gc']} " \
        f"--txpool.rejournal {config['geth_settings']['txpool.rejournal']} --txpool.accountslots {config['geth_settings']['txpool.accountslots']} " \
        f"--txpool.globalslots {config['geth_settings']['txpool.globalslots']} --txpool.accountqueue {config['geth_settings']['txpool.accountqueue']} " \
        f"--txpool.globalqueue {config['geth_settings']['txpool.globalqueue']} --txpool.lifetime {config['geth_settings']['txpool.lifetime']} --minerthreads {config['geth_settings']['minerthreads']}"

    logger.info(f"Relevant acc: {str(account_mapping)}")
    i = 0
    for index, ip in enumerate(config['ips']):
        if config['geth_settings']['num_acc'] != None:
            if len(account_mapping[ip]) == (i + 1):
                i = 0
            else:
                i += 1
            # create service file on each machine
            # --targetgaslimit config['geth_settings']['gaslimit']--targetgaslimit '30000000'
            # --rpcvhosts='*' --rpccorsdomain='*' --wsorigins='*' neeeded for the load balancer to work
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
                f"printf '%s\\n' '[Unit]' 'Description=Ethereum go client' '[Service]' 'Type=simple' "
                f"'ExecStart=/usr/bin/geth --datadir /data/gethNetwork/node/ --networkid 11 --verbosity 3 "
                f"--port 30310 --targetgaslimit '30000000' --rpc --rpcvhosts='*' --rpccorsdomain='*' --wsorigins='*' --rpcaddr 0.0.0.0  --rpcapi db,clique,miner,eth,net,web3,personal,web3,admin,txpool "
                f"--nat=extip:{config['priv_ips'][index]}  --syncmode full --allow-insecure-unlock --unlock {','.join([Web3.toChecksumAddress(x) for x in account_mapping[ip]])} "
                f"--password /data/gethNetwork/passwords.txt --mine  --etherbase {Web3.toChecksumAddress(account_mapping[ip][i])} {performance_settings}'"
                f" 'StandardOutput=file:/var/log/geth.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/geth.service")
            #logger.debug(ssh_stdout)
            #logger.debug(ssh_stderr)
            logger.debug(ssh_stdin)

            # add the keyfiles from all relevant accounts to the VMs keystores
            keystore_files = [f for f in glob.glob(acc_path + "**/*/UTC--*", recursive=True) if
                              re.match("(.*--.*--)(.*)", f).group(2) in list(set(itertools.chain(*account_mapping.values())))]
            keystore_files.sort(key=natural_keys)
            logger.info(keystore_files)
            for index_top, _ in enumerate(config['ips']):

                ssh_clients[index_top].exec_command("rm /data/gethNetwork/node/keystore/*")

                for index_lower, file in enumerate(keystore_files):
                    # TODO: only add keyfile to VM if its the right account
                    scp_clients[index_top].put(file, "/data/gethNetwork/node/keystore")


        else:
            # create service file on each machine
            # --targetgaslimit '30000000'
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
                f"printf '%s\\n' '[Unit]' 'Description=Ethereum go client' '[Service]' 'Type=simple' "
                f"'ExecStart=/usr/bin/geth --datadir /data/gethNetwork/node/ --networkid 11 --verbosity 3 "
                f"--port 30310 --targetgaslimit '30000000' --rpc --rpcvhosts='*' --rpccorsdomain='*' --wsorigins='*' --rpcaddr 0.0.0.0  --rpcapi db,clique,miner,eth,net,web3,personal,web3,admin,txpool "
                f"--nat=extip:{config['priv_ips'][index]}  --syncmode full --allow-insecure-unlock --unlock {','.join([Web3.toChecksumAddress(x) for x in account_mapping[ip]])} "
                f"--password /data/gethNetwork/passwords.txt --mine {performance_settings}' 'StandardOutput=file:/var/log/geth.log' '[Install]' "
                f"'WantedBy=default.target' > /etc/systemd/system/geth.service")
            logger.debug(ssh_stdin)

        for _, acc in enumerate(account_mapping[ip]):
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("echo 'password' >> /data/gethNetwork/passwords.txt")
            logger.debug(ssh_stdout)
            logger.debug(ssh_stderr)



    # create genesis json
    # get unique accounts from mapping
    genesis_dict = generate_genesis(accounts=list(set(itertools.chain(*account_mapping.values()))), config=config)

    with open(f"{config['exp_dir']}/setup/genesis.json", 'w') as outfile:
        json.dump(genesis_dict, outfile, indent=4)

    # push genesis from local to remote VMs
    for index, _ in enumerate(config['ips']):
        scp_clients[index].put(f"{config['exp_dir']}/setup/genesis.json", f"~/genesis.json")

        #TODO: How to log the execution of the ssh commands in a good way?
        # get account from all instances
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/genesis.json /data/gethNetwork/genesis.json")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo geth --datadir '/data/gethNetwork/node/' init /data/gethNetwork/genesis.json")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl daemon-reload")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl enable geth.service")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl start geth.service")

    enodes = []
    coinbase = []
    # collect enodes
    web3_clients = []
    logger.debug("Sleeping 3sec after starting service")
    time.sleep(3)

    for index, ip in enumerate(config['ips']):
        if config['public_ip']:
            # use public ip if exists, else it wont work
            ip_pub = config['pub_ips'][index]
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip_pub}:8545", request_kwargs={'timeout': 20})))
        else:
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip}:8545", request_kwargs={'timeout': 20})))

        enodes.append((ip, web3_clients[index].geth.admin.node_info()['enode']))

        coinbase.append(web3_clients[index].eth.coinbase)


    config['coinbase'] = coinbase
    logger.info([enode for (ip, enode) in enodes])

    with open(f"{config['exp_dir']}/setup/static-nodes.json", 'w') as outfile:
        json.dump([enode for (ip, enode) in enodes], outfile, indent=4)

    for index, _ in enumerate(config['ips']):
        scp_clients[index].put(f"{config['exp_dir']}/setup/static-nodes.json", f"~/static-nodes.json")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/static-nodes.json /data/gethNetwork/node/static-nodes.json")

    # distribute collected enodes over network
    for index, ip in enumerate(config['ips']):
        # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
        for ip_2, enode in enodes:
            # dont add own enode
            if ip != ip_2:
                web3_clients[index].geth.admin.add_peer(enode)

        logger.info("Peers: " + str(web3_clients[index].geth.admin.peers()))


    # Save geth version
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[0].exec_command("sudo geth version >> /data/geth_version.txt")
    time.sleep(2)
    scp_clients[0].get("/data/geth_version.txt", f"{config['exp_dir']}/setup/geth_version.txt")

    #TODO: move this to unit test section
    for index, ip in enumerate(config['ips']):
        # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
        logger.info("IsMining:" + str(web3_clients[index].eth.mining))
        for acc in all_accounts:
            logger.info(str(web3_clients[index].toChecksumAddress(acc)) + ": " + str(
                web3_clients[index].eth.getBalance(Web3.toChecksumAddress(acc))))


    time.sleep(3)

    for index, _ in enumerate(config['ips']):
        try:
            web3_clients[index].middleware_onion.inject(geth_poa_middleware, layer=0)
        except:
            logger.info("Middleware already injected")

    logger.info("testing if new blocks are generated across all nodes; if latest block numbers are not changing over multiple cycles something is wrong")
    for x in range(5):
        for index, _ in enumerate(web3_clients):
            logger.info(str(web3_clients[index].eth.blockNumber))

        logger.info("----------------------------------")
        time.sleep(10)


def get_relevant_account_mapping(accounts, config):
    """
    returns the array with the relevant accounts for the genesis and unlock process
    :param accounts:
    :param config:
    :return:
    """

    if config[f"{config['blockchain_type']}_settings"]['num_acc'] is None:
        return {ip: [account] for (ip, account) in zip(config['ips'], accounts)}
    else:
        rnd_accounts = np.random.choice(a=accounts, replace=False, size=config[f"{config['blockchain_type']}_settings"]['num_acc'])
        return {ip: rnd_accounts for ip in config['ips']}


def generate_genesis(accounts, config):
    """
    # TODO make it more dynamic to user desires
    # https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority
    :param config: config containing the specs for genesis
    :param accounts: accounts to be added to signers/added some balance
    :return: genesis dictonary
    """

    balances = [config['geth_settings']['balance'] for x in accounts]
    base_balances = {"0000000000000000000000000000000000000001": {"balance": "1"},
                     "0000000000000000000000000000000000000002": {"balance": "1"},
                     "0000000000000000000000000000000000000003": {"balance": "1"},
                     "0000000000000000000000000000000000000004": {"balance": "1"},
                     "0000000000000000000000000000000000000005": {"balance": "1"},
                     "0000000000000000000000000000000000000006": {"balance": "1"},
                     "0000000000000000000000000000000000000007": {"balance": "1"},
                     "0000000000000000000000000000000000000008": {"balance": "1"}}
    additional_balances = {str(x): {"balance": str(y)} for x, y in zip(accounts, balances)}
    merged_balances = {**base_balances, **additional_balances}

    # clique genesis at beginning
    genesis_dict = {

        "config": {
            'chainId': config['geth_settings']['chain_id'],
            'homesteadBlock': 0,
            "constantinopleBlock": 0,
            'eip150Block': 0,
            'eip155Block': 0,
            'eip158Block': 0,
            'byzantiumBlock': 0,
            'clique': {
                'period': config['geth_settings']['period'],
                'epoch': config['geth_settings']['epoch']
            }
        },
        "alloc": merged_balances,
        "coinbase": "0x0000000000000000000000000000000000000000",
        "difficulty": "0x1",
        "extraData": f"0x0000000000000000000000000000000000000000000000000000000000000000{''.join(accounts)}"
        f"0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "gasLimit": config['geth_settings']['gaslimit'],
        "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "nonce": "0x0000000000000042",
        "timestamp": config['geth_settings']['timestamp']

    }
    return genesis_dict


def restart_network(config, ssh_clients, logger):
    """
    Restarts the services of all networks and cleans the transaction pools
    :param config:
    :param ssh_clients:
    :param index:
    :param logger:
    :return:
    """

    # first stop all nodes
    for index, client in enumerate(ssh_clients):
        kill_node(config, ssh_clients, index, logger)
        delete_pool(ssh_clients, index, logger)

    # second start all nodes again
    for index, client in enumerate(ssh_clients):
        revive_node(config, ssh_clients, index, logger)

    logger.debug("All nodes should now be restarted")


def kill_node(config, ssh_clients, index, logger):
    """

    :param config:
    :param ssh_clients:
    :param index:
    :param logger:
    :return:
    """
    logger.debug("stopping geth service...")
    channel = ssh_clients[index].get_transport().open_session()
    channel.exec_command("sudo service geth stop")
    channel.exec_command("sudo rm /var/log/geth.log")


def delete_pool(ssh_clients, index, logger):
    """

    :param ssh_clients:
    :param index:
    :param logger:
    :return:
    """
    stdin, stdout, stderr = ssh_clients[index].exec_command("sudo rm /data/gethNetwork/node/geth/transactions.rlp")
    logger.debug(stdout.readlines())
    logger.debug(stderr.readlines())


def revive_node(config, ssh_clients, index, logger):
    """

    :param config:
    :param ssh_clients:
    :param index:
    :param logger:
    :return:
    """

    restart_count = 0
    while restart_count < 5:
        logger.debug(f"restarting geth for the {restart_count}x time...")
        channel = ssh_clients[index].get_transport().open_session()
        channel.exec_command("sudo service geth start")

        # Give Geth couple of seconds to start
        time.sleep(3)
        # test if restart was successful
        if config['public_ip']:
            # use public ip if exists, else it wont work
            web3_client = Web3(Web3.HTTPProvider(f"http://{config['pub_ips'][index]}:8545", request_kwargs={'timeout': 20}))
        else:
            web3_client = Web3(Web3.HTTPProvider(f"http://{config['ips'][index]}:8545", request_kwargs={'timeout': 20}))

        web3_client.middleware_onion.inject(geth_poa_middleware, layer=0)

        if web3_client.eth.blockNumber > 0:
            logger.info(f"blockNumber is {web3_client.eth.blockNumber}. Restart seems successful.")
            logger.info(f"TxPool Status: {web3_client.geth.txpool.status()}")
            return True
        else:
            kill_node(config, ssh_clients, index, logger)
            delete_pool(ssh_clients, index, logger)

    logger.error("Restart was NOT successful")
    return False


def atoi(text):
    return int(text) if text.isdigit() else text


def natural_keys(text):
    """
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    :param text:
    :return:
    """
    return [atoi(c) for c in re.split(r'(\d+)', text)]
