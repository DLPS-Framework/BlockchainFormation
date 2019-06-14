import glob
import itertools
import json
import os
import re
import time
import numpy as np
from web3 import Web3
import web3
from web3.middleware import geth_poa_middleware
import toml

from ec2_automation.blockchain_specifics.Geth import natural_keys, get_relevant_account_mapping

#TODO: Make code more efficient and nicer
#TODO: improve natural sorting stuff


########## U G L Y  M O N K E Y P A T C H ##################
#web3 does not support request retry function, therefore we inject it ourselves
#https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests/47475019#47475019
import lru
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from web3.utils.caching import (
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

web3.utils.request._get_session = _get_session_new

#############################################


def parity_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the geth specific shutdown operations (e.g. pulling the geth logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['ips']):
        # get account from all instances
        try:
            scp_clients[index].get("/var/log/parity.log",
                                   f"{config['exp_dir']}/parity_logs/parity_log_node_{index}.log")
            scp_clients[index].get("/var/log/user_data.log",
                                   f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

        except:
            logger.info("Parity logs could not be pulled from the machines.")


def verify_key(f, list):
    with open(f) as json_file:
        data = json.load(json_file)
        print(list)
        #to checksum somehow makes capital letters
        if Web3.toChecksumAddress(data['address']).lower() in [x.lower() for x in list]:
            return True
        else:
            return False

def parity_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """

    acc_path = os.getcwd()
    os.mkdir(f"{acc_path}/{config['exp_dir']}/accounts")
    # enodes dir not needed anymore since enodes are saved in static-nodes file
    # os.mkdir((f"{path}/{self.config['exp_dir']}/enodes"))
    os.mkdir((f"{acc_path}/{config['exp_dir']}/parity_logs"))

    #generate basic spec and node.toml

    spec_dict = generate_spec(accounts=None, config=config)
    with open(f"{config['exp_dir']}/spec_basic.json", 'w') as outfile:
        json.dump(spec_dict, outfile)

    with open(f"{config['exp_dir']}/node_basic.toml", 'w') as outfile:
        #dummy signer accounts, gets replaced later anyway with real signers
        toml.dump(generate_node_dict("0x50fc1dd12e1534704a375f3c9acb14eb5f1f3469"), outfile)

    #put spec and node on VM
    for index, _ in enumerate(config['ips']):
        scp_clients[index].put(f"{config['exp_dir']}/spec_basic.json", f"~/spec.json")
        scp_clients[index].put(f"{config['exp_dir']}/node_basic.toml", f"~/node.toml")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/spec.json /data/parityNetwork/spec.json")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/node.toml /data/parityNetwork/node.toml")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
             "sudo bash -c  'bash <(curl https://get.parity.io -L) -r stable'")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        #"sudo bash -c  'bash <(wget -O - http://get.parity.io) -r stable'"
        # ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
        #     "sudo bash -c  'bash <(wget -O - http://get.parity.io) -r stable'")
        #sudo bash -c  'wget -O - http://get.parity.io | bash'
        # while "Could not resolve proxy" in ssh_stderr or ssh_stderr:
        #     ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
        #         "sudo bash -c  'bash <(curl https://get.parity.io -L)'")
        # try:
        #     logger.info(f"Log node {index} {ssh_stdout.read().decode('utf-8').encode('utf-8')}")
        #     logger.info(f"Log node {index} {ssh_stderr.read().decode('utf-8').encode('utf-8')}")
        # except:
        #     pass
        # create account
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo parity account new --config /data/parityNetwork/node.toml > /data/parityNetwork/account.txt")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        #logger.info(ssh_stdin.read().decode('ascii'))
        time.sleep(1)
        # get accounts and keys
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo cp -vr /data/parityNetwork/keys/DemoPoA /data")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo chown -R ubuntu /data/DemoPoA/")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo chown -R ubuntu /data/parityNetwork/keys/DemoPoA")



        scp_clients[index].get("/data/parityNetwork/account.txt",
                               f"{config['exp_dir']}/accounts/account_node_{index}.txt")
        scp_clients[index].get("/data/DemoPoA",
                               f"{config['exp_dir']}/accounts/keystore_node_{index}", recursive=True)

        time.sleep(0.5)
    all_accounts = []

    acc_path = f"{config['exp_dir']}/accounts"
    file_list = os.listdir(acc_path)
    #Sorting to get matching accounts to ip
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

    #which node gets which account unlocked
    account_mapping = get_relevant_account_mapping(all_accounts, config)

    logger.info(f"Relevant acc: {str(account_mapping)}")

    #get new spec and node.toml
    #every node needs specific node.toml because of signers



    #get unique accounts from mapping
    spec_dict = generate_spec(accounts=list(set(itertools.chain(*account_mapping.values()))), config=config)
    #self.pprnt.pprint(genesis_dict)

    with open(f"{config['exp_dir']}/spec.json", 'w') as outfile:
        json.dump(spec_dict, outfile)



    i = 0
    for index, ip in enumerate(config['ips']):

        if len(account_mapping[ip]) == (i + 1):
            i = 0
        else:
            i += 1
        # create service file on each machine

        with open(f"{config['exp_dir']}/node_node_{index}.toml", 'w') as outfile:

            toml.dump(generate_node_dict(signers=Web3.toChecksumAddress(account_mapping[ip][i]),
                                         unlock=[Web3.toChecksumAddress(x) for x in account_mapping[ip]]), outfile)

        # add the keyfiles from all relevant accounts to the VMs keystores
        keystore_files = [f for f in glob.glob(acc_path + "**/*/UTC--*", recursive=True)
                          if verify_key(f, list(set(itertools.chain(*account_mapping.values()))))]
        keystore_files.sort(key=natural_keys)
        logger.info(keystore_files)
        for index_top, ip in enumerate(config['ips']):

            ssh_clients[index_top].exec_command("rm /data/parityNetwork/keys/DemoPoA/*")

            for index_lower, file in enumerate(keystore_files):
                # TODO: only add keyfile to VM if its the right account
                # distribute all accounts to nodes
                scp_clients[index_top].put(file, "/data/parityNetwork/keys/DemoPoA")

        for _, acc in enumerate(account_mapping[ip]):
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("echo 'password' >> /data/parityNetwork/passwords.txt")
            logger.debug(ssh_stdout)
            logger.debug(ssh_stderr)

        scp_clients[index].put(f"{config['exp_dir']}/spec.json", f"~/spec.json")

        # TODO: How to log the execution of the ssh commands in a good way?
        # get account from all instances
        scp_clients[index].put(f"{config['exp_dir']}/spec.json", f"~/spec.json")

        # replace spec and node on VMs
        # remove old node.toml
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo rm /data/parityNetwork/node.toml")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo rm /data/parityNetwork/spec.json")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        scp_clients[index].put(f"{config['exp_dir']}/node_node_{index}.toml", f"~/node.toml")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/spec.json /data/parityNetwork/spec.json")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/node.toml /data/parityNetwork/node.toml")
        logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        # start service
        #ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
        #    "sudo parity daemon --config node.toml  --log-file /var/log/parity.log")
        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl daemon-reload")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl enable parity.service")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl start parity.service")

    logger.debug("service should now have been started")

    enodes = []
    # collect enodes
    web3_clients = []
    time.sleep(15)

    for index, ip in enumerate(config['ips']):
        if config['public_ip']:
            # use public ip if exists, else it wont work
            ip_pub = config['public_ips'][index]
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip_pub}:8545", request_kwargs={'timeout': 5})))
        else:
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip}:8545", request_kwargs={'timeout': 5})))
        # print(web3.admin)
        enodes.append((ip, web3_clients[index].parity.enode()))
        #web3_clients[index].miner.stop()
        logger.info(f"Coinbase of {ip}: {web3_clients[index].eth.coinbase}")



    #Does sleep fix the Max retries exceeded with url?
    #time.sleep(3)
    logger.info([enode for (ip, enode) in enodes])

    with open(f"{config['exp_dir']}/static-nodes.json", 'w') as outfile:
        json.dump([enode for (ip, enode) in enodes], outfile)

    #FIXME: addReservedPeer(enode) not in current web3.py package

    with open(f"{config['exp_dir']}/peers.txt", 'w') as filehandle:
        filehandle.writelines("%s\n" % enode for (ip, enode) in enodes)



    for index, ip in enumerate(config['ips']):

        node_toml = toml.load(f"{config['exp_dir']}/node_node_{index}.toml")
        node_toml['network']['reserved_peers'] = "/data/parityNetwork/peers.txt"
        with open(f"{config['exp_dir']}/node_node_{index}.toml", 'w') as outfile:
          toml.dump(node_toml, outfile)

        scp_clients[index].put(f"{config['exp_dir']}/node_node_{index}.toml", f"~/node.toml")
        scp_clients[index].put(f"{config['exp_dir']}/peers.txt", f"~/peers.txt")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/node.toml /data/parityNetwork/node.toml")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/peers.txt /data/parityNetwork/peers.txt")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo service parity stop")
        time.sleep(3)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo rm /var/log/parity.log")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo service parity start")

    time.sleep(10)

    #TODO: move this to unit test section
    for index, ip in enumerate(config['ips']):
        # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
        logger.info("IsMining:" + str(web3_clients[index].eth.mining))
        for acc in all_accounts:
            logger.info(str(web3_clients[index].toChecksumAddress(acc)) + ": " + str(
                web3_clients[index].eth.getBalance(Web3.toChecksumAddress(acc))))

    logger.info("Since parity takes ages for the first blocks, it is time to sleep for two minuted zZz")
    time.sleep(120)
    logger.info("zZz Just one more minute zZz")
    time.sleep(60)

    for index, _ in enumerate(config['ips']):
        try:
            web3_clients[index].middleware_stack.inject(geth_poa_middleware, layer=0)
        except:
            logger.info("Middleware already injected")

    logger.info("testing if new blocks are generated across all nodes; if latest block numbers are not changing over multiple cycles something is wrong")
    for x in range(15):
        for index, _ in enumerate(web3_clients):
            logger.info(web3_clients[index].eth.getBlock('latest')['number'])

        logger.info("----------------------------------")
        time.sleep(10)


def generate_node_dict(signers, unlock=None, reserved_peers= False):
    """
    TODO
    :return:
    """

    node_dict =\
        {
                'account': {'password': ['/data/parityNetwork/password.txt']

                            },
                'mining': {
                            'engine_signer': signers,
                            'reseal_on_txs': 'none'
                            },
                'network': {
                            'port': 30300
                            },
                'parity': {
                            'base_path': '/data/parityNetwork', 'chain': '/data/parityNetwork/spec.json'
                          },
                'rpc': {
                    'apis': ['web3', 'eth', 'net', 'personal', 'parity', 'parity_set', 'traces', 'rpc', 'parity_accounts'],
                    'port': 8545,
                    'interface': '0.0.0.0'
                       },
                'websockets': {'port': 8450}
         }

    if unlock != None:
        node_dict['account']['unlock'] = unlock

        node_dict['account']['password'] = ['/data/parityNetwork/passwords.txt']
    if reserved_peers:
        node_dict['network']['reserved_peers'] = "/data/parityNetwork/peers.txt"

    #if signers != None:
      #  node_dict['mining']['engine_signer'] = signers

    return node_dict

def generate_spec(accounts, config):
    """
    #TODO make it more dynamic to user desires
    # https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority
    :param accounts: accounts to be added to signers/added some balance
    :return: spec dictonary
    """
    #config['parity_settings']['stepDuration']

    base_balances = {"0x0000000000000000000000000000000000000001": {"balance": "1", "builtin": {"name": "ecrecover", "pricing": {"linear": {"base": 3000, "word": 0}}}},
                     "0x0000000000000000000000000000000000000002": {"balance": "1", "builtin": {"name": "sha256", "pricing": {"linear": {"base": 60, "word": 12 }}}},
                     "0x0000000000000000000000000000000000000003": {"balance": "1", "builtin": {"name": "ripemd160", "pricing": {"linear": {"base": 600, "word": 120}}}},
                     "0x0000000000000000000000000000000000000004": {"balance": "1", "builtin": {"name": "identity", "pricing": {"linear": {"base": 15, "word": 3}}}}}
    if accounts != None:
        balances = [config['parity_settings']['balance'] for x in accounts]
        additional_balances = {str(x): {"balance": str(y)} for x, y in zip(accounts, balances)}
        merged_balances = {**base_balances, **additional_balances}
    else:
        merged_balances = base_balances
        accounts = []

    spec_dict ={
                 "name": "DemoPoA",
                 "engine": {
                         "authorityRound": {
                                     "params": {
                                                 "stepDuration": config['parity_settings']['step_duration'],
                                                 "validators" : {
                                                 "list": accounts
                                                                 }
                                                 }
                                            }
                         },
                 "params": {
                             "gasLimitBoundDivisor": "0x400",
                             "maximumExtraDataSize": "0x20",
                             "minGasLimit": "0x1388",
                             "networkID": "0x2323",
                             "eip155Transition": 0,
                             "validateChainIdTransition": 0,
                             "eip140Transition": 0,
                             "eip211Transition": 0,
                             "eip214Transition": 0,
                             "eip658Transition": 0
                            },
                 "genesis": {
                 "seal": {
                         "authorityRound": {
                                             "step": "0x0",
                                             "signature": "0x0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"
                                           }
                         },
                 "difficulty": "0x20000",
                 "gasLimit": "0x5B8D80"
                 },
                 "accounts": merged_balances
                }

    return spec_dict