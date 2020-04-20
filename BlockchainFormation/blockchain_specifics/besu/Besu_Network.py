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

import json
import os
import rlp

from BlockchainFormation.utils.utils import *

########## U G L Y  M O N K E Y P A T C H ##################
# web3 does not support request retry function, therefore we inject it ourselves
# https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests/47475019#47475019
import lru
import numpy as np
import requests
import web3
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from web3 import Web3
from web3._utils.caching import (
    generate_cache_key,
)
from web3.middleware import geth_poa_middleware


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

######################################################


class Besu_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the besu specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the besu specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        # the indices of the blockchain nodes
        config['node_indices'] = list(range(0, config['vm_count']))
        config['groups'] = [config['node_indices']]

        logger.info("Conducting the startup for IBFT")

        # replacing block time and number of nodes
        stdin, stdout, stderr = ssh_clients[0].exec_command("sed -i -e 's/substitute_count/'" + f"'{config['vm_count']}'" + "'/g' /data/IBFT-Network/ibftConfigFile.json")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command("sed -i -e 's/substitute_count/'" + f"'{config['vm_count']-1}'" + "'/g' /data/make_dirs.sh")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command("sed -i -e 's/substitute_period/'" + f"'{config['besu_settings']['block_period']}'" + "'/g' /data/IBFT-Network/ibftConfigFile.json")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())


        logger.info("Generating all the files on the first node and distributing them")
        stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/IBFT-Network && . ~/.profile && besu operator generate-blockchain-config --config-file=ibftConfigFile.json --to=networkFiles --private-key-file-name=key)")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        stdin, stdout, stderr = ssh_clients[0].exec_command("/data/make_dirs.sh")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())


        logger.info("Getting the config on the coordinator and distributing to the nodes")
        scp_clients[0].get("/data/IBFT-Network", f"{config['exp_dir']}", recursive=True)

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].put(f"{config['exp_dir']}/IBFT-Network/Node_{index}", "/data", recursive=True)

        addresses = []
        keys = []
        logger.info("Getting the keys and addresses of all coinbases")
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[0].exec_command(f". ~/.profile && besu --data-path=/data/IBFT-Network/Node_{index}/data public-key export-address --to=/data/IBFT-Network/Node_{index}/data/address")
            logger.info(stdout.readlines())
            logger.info(stderr.readlines())

            stdin, stdout, stderr = ssh_clients[0].exec_command(f"cat /data/IBFT-Network/Node_{index}/data/address")
            out = stdout.readlines()

            logger.info(out)
            logger.info(stderr.readlines())

            address = out[0].replace("\n", "")
            logger.info(f"Address: {address}")
            addresses.append(address)

            stdin, stdout, stderr = ssh_clients[index].exec_command(f"cat /data/Node_{index}/data/key")
            out = stdout.readlines()

            logger.info(out)
            logger.info(stderr.readlines())

            key = out[0].replace("\n", "")
            logger.info(f"Key: {key}")
            keys.append(key)


        logger.info("Replacing the alloc address")

        genesis_file = open(f"{config['exp_dir']}/IBFT-Network/Node_0/genesis.json")
        genesis_json = json.load(genesis_file)
        genesis_file.close()

        logger.info(f"Genesis_json: {genesis_json}")

        allocs = {}

        for index, _ in enumerate(config['priv_ips']):
            allocs[f"{addresses[index]}"] = {"balance": "90000000000000000000000"}

        logger.info(f"Allocs: {allocs}")
        genesis_json["alloc"] = allocs

        logger.info(f"Genesis_json: {genesis_json}")

        file = open(f"{config['exp_dir']}/IBFT-Network/Node_0/genesis.json", "w+")
        json.dump(genesis_json, file, indent=4)
        file.close()

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].put(f"{config['exp_dir']}/IBFT-Network/Node_0/genesis.json", f"/data/Node_{index}/genesis.json")


        logger.info("Starting the first node and getting its enode")
        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command(f'(cd /data/Node_0 && . ~/.profile && besu --data-path=data --genesis-file=./genesis.json --rpc-http-enabled --rpc-http-api=ETH,NET,IBFT --host-whitelist="*" --rpc-http-cors-origins="all" --rpc-http-host=0.0.0.0 --rpc-http-port=8545 --p2p-host={config["priv_ips"][0]} >> node.log)')

        time.sleep(10)

        stdin, stdout, stderr = ssh_clients[0].exec_command("(cd /data/Node_0 && cat node.log | grep enode | awk '{print $12}')")
        out = stdout.readlines()[0]

        logger.info(out)
        logger.info(stdout.readlines())

        enode = out.replace("\n", "")

        logger.info("Starting the remaining nodes")
        for index, _ in enumerate(config['priv_ips']):
            if index != 0:
                channel = ssh_clients[index].get_transport().open_session()
                channel.exec_command(f'(cd /data/Node_{index} && . ~/.profile &&  besu --data-path=data --genesis-file=./genesis.json --bootnodes={enode} --p2p-port=30303 --rpc-http-enabled --rpc-http-api=ETH,NET,IBFT --host-whitelist="*" --rpc-http-cors-origins="all" --rpc-http-host=0.0.0.0 --rpc-http-port=8545 --p2p-host={config["priv_ips"][index]} >> node.log)')


        time.sleep(10)

        enodes = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"(cd /data/Node_{index} " + "&& cat node.log | grep enode | awk '{print $12}')")
            out = stdout.readlines()[0]

            logger.info(out)
            logger.info(stderr.readlines())

            enodes.append(out.replace("\n", ""))

        config['enodes'] = enodes

        logger.info(f"All enodes: {config['enodes']}")

        enodes = []
        coinbase = []
        # collect enodes
        web3_clients = []
        logger.debug("Sleeping 3sec")
        time.sleep(3)

        coinbase = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command('curl -sX POST --data \'{"jsonrpc":"2.0","method":"eth_coinbase","params":[],"id":64}\' ' + f'http://{config["priv_ips"][index]}:8545 | jq ".result"')
            out = stdout.readlines()

            logger.info(out)
            logger.info(stderr.readlines())

            coinbase.append(out[0].replace("\n", "").replace("\"", ""))

        config['coinbase'] = coinbase
        logger.info(f"Coinbase: {coinbase}")

        """
        for index, ip in enumerate(config['priv_ips']):
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{config['pub_ips'][index]}:8545", request_kwargs={'timeout': 20})))
            web3_clients[index].middleware_onion.inject(geth_poa_middleware, layer=0)

            enodes.append((ip, web3_clients[index].geth.admin.node_info()['enode']))

            coinbase.append(web3_clients[index].eth.coinbase)

        config['coinbase'] = coinbase
        logger.info(f"Coinbases: {config['coinbase']}")
        logger.info([enode for (ip, enode) in enodes])
        """

        logger.info("Getting the private keys")
        keys = []
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"cat /data/Node_{index}/data/key")
            out = stdout.readlines()

            logger.info(out)
            logger.info(stderr.readlines())

            keys.append(out[0].replace("\n", ""))

        config['keys'] = keys
        logger.info(f"Keys: {config['keys']}")

        logger.info("Getting the balance of the first node")
        stdin, stdout, stderr = ssh_clients[0].exec_command('curl -s -X POST --data \'{"jsonrpc":"2.0", "method":"eth_getBalance",' + f'"params":["{addresses[0]}", "latest"]' + ', "id":1}\'' + f' http://{config["priv_ips"][0]}:8545')
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        logger.info("Getting the balance of the last node")
        stdin, stdout, stderr = ssh_clients[-1].exec_command('curl -s -X POST --data \'{"jsonrpc":"2.0", "method":"eth_getBalance",' + f'"params":["{addresses[-1]}", "latest"]' + ', "id":1}\'' + f' http://{config["priv_ips"][-1]}:8545')
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        """

        logger.info("Sending some ether to all other nodes")
        for index, _ in enumerate(config['priv_ips']):
            if index != 0:
                logger.info('curl -X POST --data \'{"jsonrpc":"2.0","method":"eth_sendTransaction","params":[{' + f'"from": {address}, "to": {coinbase[index]}, "value": 100000, "gas": "0x76c0", "gasPrice": "0x9184e72a000"' + '}],"id":1}\'' + f' http://{config["priv_ips"][0]}:8545')
                stdin, stdout, stderr = ssh_clients[0].exec_command('curl -X POST --data \'{"jsonrpc":"2.0","method":"eth_sendTransaction","params":[{' + f'"from": {address}, "to": {coinbase[index]}, "value": 100000, "gas": "0x76c0", "gasPrice": "0x9184e72a000"' + '}],"id":1}\'' + f' http://{config["priv_ips"][0]}:8545')
                logger.info(stdout.readlines())
                logger.info(stderr.readlines())


        logger.info("Getting the balance of the last node")
        stdin, stdout, stderr = ssh_clients[-1].exec_command('curl -s -X POST --data \'{"jsonrpc":"2.0", "method":"eth_getBalance",' + f'"params":["{coinbase[-1]}", "latest"]' + ', "id":1}\'' + f' http://{config["priv_ips"][-1]}:8545')
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())
        
        """