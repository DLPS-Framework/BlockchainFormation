import glob
import itertools
import json
import os
import time
from web3 import Web3
import web3
from web3.middleware import geth_poa_middleware
import toml

from BlockchainFormation.blockchain_specifics.Geth.Geth import natural_keys, get_relevant_account_mapping

#TODO: Make code more efficient and nicer
#TODO: improve natural sorting stuff


########## U G L Y  M O N K E Y P A T C H ##################
# web3 does not support request retry function, therefore we inject it ourselves
# https://stackoverflow.com/questions/23013220/max-retries-exceeded-with-url-in-requests/47475019#47475019
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
    :param config: config dict
    :param logger: logger
    :param ssh_clients: ssh clients for all VMs in config
    :param scp_clients: scp clients for all VMs in config
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
    """
    checks if address in provided file f is in account list
    :param f: filename with account data
    :param list: list of verified accounts
    :return:
    """
    with open(f) as json_file:
        data = json.load(json_file)
        #print(list)
        # to checksum makes capital letters
        if Web3.toChecksumAddress(data['address']).lower() in [x.lower() for x in list]:
            return True
        else:
            return False

def parity_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :param config: config dict
    :param logger: logger
    :param ssh_clients: ssh clients for all VMs in config
    :param scp_clients: scp clients for all VMs in config
    :return:
    """

    #acc_path = os.getcwd()
    os.mkdir(f"{config['exp_dir']}/setup/accounts")
    # enodes dir not needed anymore since enodes are saved in static-nodes file
    # os.mkdir((f"{path}/{self.config['exp_dir']}/enodes"))
    os.mkdir((f"{config['exp_dir']}/parity_logs"))

    # generate basic spec and node.toml
    spec_dict = generate_spec(accounts=None, config=config)
    with open(f"{config['exp_dir']}/setup/spec_basic.json", 'w') as outfile:
        json.dump(spec_dict, outfile, indent=4)

    with open(f"{config['exp_dir']}/setup/node_basic.toml", 'w') as outfile:
        # dummy signer accounts, gets replaced later anyway with real signers
        toml.dump(generate_node_dict("0x50fc1dd12e1534704a375f3c9acb14eb5f1f3469"), outfile)

    # put spec and node on VM
    for index, _ in enumerate(config['ips']):
        scp_clients[index].put(f"{config['exp_dir']}/setup/spec_basic.json", f"~/spec.json")
        scp_clients[index].put(f"{config['exp_dir']}/setup/node_basic.toml", f"~/node.toml")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/spec.json /data/parityNetwork/spec.json")
        logger.debug(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.debug(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/node.toml /data/parityNetwork/node.toml")
        logger.debug(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        logger.debug(f"Log node {index} {ssh_stderr.read().decode('ascii')}")




        # check if install was successful
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo bash -c  'command -v parity'")
        parity_install_check = ssh_stdout.read().decode('ascii')
        logger.debug(f"Log node {index} {parity_install_check}")
        i = 1

        while parity_install_check != "/usr/bin/parity\n":
            # FIXME find a stable way to install parity instead of this bruteforce approach

            if i == 15:
                logger.debug("Parity installation failed at least 15 times on one of the nodes!")
                raise ParityInstallFailed

            logger.info(f"{i}. try to install parity on node {index}")

            # trying to install parity
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
                "sudo bash -c  'bash <(curl https://get.parity.io -L) -r stable'")
            logger.debug(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
            logger.debug(f"Log node {index} {ssh_stderr.read().decode('ascii')}")


            # check if install was successful
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
                "sudo bash -c  'command -v parity'")
            parity_install_check = ssh_stdout.read().decode('ascii')
            logger.info(f"Log node {index} {parity_install_check}")
            #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")

            i += 1

        # create account
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo parity account new --config /data/parityNetwork/node.toml > /data/parityNetwork/account.txt")
        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
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
                               f"{config['exp_dir']}/setup/accounts/account_node_{index}.txt")
        scp_clients[index].get("/data/DemoPoA",
                               f"{config['exp_dir']}/setup/accounts/keystore_node_{index}", recursive=True)

        time.sleep(0.5)
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

    logger.info(f"Relevant acc: {str(account_mapping)}")

    #get unique accounts from mapping
    spec_dict = generate_spec(accounts=list(set(itertools.chain(*account_mapping.values()))), config=config)
    #self.pprnt.pprint(genesis_dict)

    with open(f"{config['exp_dir']}/setup/spec.json", 'w') as outfile:
        json.dump(spec_dict, outfile, indent=4)



    i = 0
    for index, ip in enumerate(config['ips']):

        if len(account_mapping[ip]) == (i + 1):
            i = 0
        else:
            i += 1
        # create service file on each machine

        with open(f"{config['exp_dir']}/setup/node_node_{index}.toml", 'w') as outfile:

            toml.dump(generate_node_dict(signers=Web3.toChecksumAddress(account_mapping[ip][i]),
                                         unlock=[Web3.toChecksumAddress(x).lower() for x in account_mapping[ip]]), outfile)

        # add the keyfiles from all relevant accounts to the VMs keystores
        keystore_files = [f for f in glob.glob(acc_path + "**/*/UTC--*", recursive=True)
                          if verify_key(f, list(set(itertools.chain(*account_mapping.values()))))]
        keystore_files.sort(key=natural_keys)
        logger.debug(keystore_files)
        for index_top, ip in enumerate(config['ips']):

            ssh_clients[index_top].exec_command("rm /data/parityNetwork/keys/DemoPoA/*")

            for index_lower, file in enumerate(keystore_files):
                # TODO: only add keyfile to VM if its the right account
                # distribute all accounts to nodes
                scp_clients[index_top].put(file, "/data/parityNetwork/keys/DemoPoA")

        for _, acc in enumerate(account_mapping[ip]):
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("echo 'password' >> /data/parityNetwork/passwords.txt")
            #logger.debug(ssh_stdout)
            #logger.debug(ssh_stderr)

        scp_clients[index].put(f"{config['exp_dir']}/setup/spec.json", f"~/spec.json")

        # TODO: How to log the execution of the ssh commands in a good way?
        # get account from all instances
        scp_clients[index].put(f"{config['exp_dir']}/setup/spec.json", f"~/spec.json")

        # replace spec and node on VMs
        # remove old node.toml
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo rm /data/parityNetwork/node.toml")
        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo rm /data/parityNetwork/spec.json")
        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        scp_clients[index].put(f"{config['exp_dir']}/setup/node_node_{index}.toml", f"~/node.toml")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/spec.json /data/parityNetwork/spec.json")
        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/node.toml /data/parityNetwork/node.toml")
        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")

        #logger.info(f"Log node {index} {ssh_stdout.read().decode('ascii')}")
        #logger.info(f"Log node {index} {ssh_stderr.read().decode('ascii')}")


        #start service
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl daemon-reload")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl enable parity.service")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl start parity.service")

    logger.debug("service should now have been started")

    time.sleep(10)
    for index, ip in enumerate(config['ips']):
        # Is this really needed?
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo service parity restart")

    enodes = []
    # collect enodes
    web3_clients = []
    time.sleep(20)

    for index, ip in enumerate(config['ips']):
        if config['public_ip']:
            # use public ip if exists, else it wont work
            ip_pub = config['public_ips'][index]
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip_pub}:8545", request_kwargs={'timeout': 5})))
        else:
            web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip}:8545", request_kwargs={'timeout': 5})))

        enodes.append((ip, web3_clients[index].parity.enode()))
        #web3_clients[index].miner.stop()
        logger.info(f"Coinbase of {ip}: {web3_clients[index].eth.coinbase}")



    logger.info([enode for (ip, enode) in enodes])

    with open(f"{config['exp_dir']}/setup/static-nodes.json", 'w') as outfile:
        json.dump([enode for (ip, enode) in enodes], outfile, indent=4)

    #FIXME: addReservedPeer(enode) not in current web3.py package

    with open(f"{config['exp_dir']}/setup/peers.txt", 'w') as filehandle:
        filehandle.writelines("%s\n" % enode for (ip, enode) in enodes)



    for index, ip in enumerate(config['ips']):

        node_toml = toml.load(f"{config['exp_dir']}/setup/node_node_{index}.toml")
        node_toml['network']['reserved_peers'] = "/data/parityNetwork/peers.txt"
        with open(f"{config['exp_dir']}/setup/node_node_{index}.toml", 'w') as outfile:
            toml.dump(node_toml, outfile)

        scp_clients[index].put(f"{config['exp_dir']}/setup/node_node_{index}.toml", f"~/node.toml")
        scp_clients[index].put(f"{config['exp_dir']}/setup/peers.txt", f"~/peers.txt")

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/node.toml /data/parityNetwork/node.toml")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/peers.txt /data/parityNetwork/peers.txt")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo service parity stop")
        time.sleep(3)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo rm /var/log/parity.log")
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo service parity start")

    time.sleep(10)


    # Save parity version
    ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[0].exec_command("parity --version > /data/parity_version.txt")
    scp_clients[0].get("/data/parity_version.txt", f"{config['exp_dir']}/setup/parity_version.txt")

    #TODO: move this to unit test section
    for index, ip in enumerate(config['ips']):
        # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
        logger.info("IsMining:" + str(web3_clients[index].eth.mining))
        for acc in all_accounts:
            logger.info(str(web3_clients[index].toChecksumAddress(acc)) + ": " + str(
                web3_clients[index].eth.getBalance(Web3.toChecksumAddress(acc))))

    logger.info("Since parity takes ages for the first blocks, it is time to sleep for two minutes zZz")
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
    Generates node dictionary needed for creation of node.toml
    :param signers: which account to be signer
    :param unlock: which accounts to unlock
    :param reserved_peers: which nodes are connected to each other
    :return:
    """

    node_dict =\
        {
                'account': {'password': ['/data/parityNetwork/password.txt']

                            },
                'mining': {
                            'engine_signer': signers.lower(),
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
                    'interface': '0.0.0.0',
                    'hosts': ['all'],
                    'cors': ['all']
                       },
                'websockets': {
                    'port': 8450,
                    'interface' : "0.0.0.0",
                    'origins' : ["all"],
                    'apis' : ["web3", "eth", "pubsub", "net", "parity", "parity_pubsub", "traces", "rpc", "shh", "shh_pubsub"],
                    'hosts' : ["all"]
    },
                'footprint': {
                    'pruning': 'archive'
                }

         }

    if unlock is not None:
        node_dict['account']['unlock'] = unlock

        node_dict['account']['password'] = ['/data/parityNetwork/passwords.txt']
    if reserved_peers:
        node_dict['network']['reserved_peers'] = "/data/parityNetwork/peers.txt"

    return node_dict

def generate_spec(accounts, config):
    """
    #TODO make it more dynamic to user desires
    # https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority
    :param accounts: accounts to be added to signers/added some balance
    :param config: config dict
    :return: spec dictonary
    """

    base_balances = {"0x0000000000000000000000000000000000000001": {"balance": "1", "builtin": {"name": "ecrecover", "pricing": {"linear": {"base": 3000, "word": 0}}}},
                     "0x0000000000000000000000000000000000000002": {"balance": "1", "builtin": {"name": "sha256", "pricing": {"linear": {"base": 60, "word": 12}}}},
                     "0x0000000000000000000000000000000000000003": {"balance": "1", "builtin": {"name": "ripemd160", "pricing": {"linear": {"base": 600, "word": 120}}}},
                     "0x0000000000000000000000000000000000000004": {"balance": "1", "builtin": {"name": "identity", "pricing": {"linear": {"base": 15, "word": 3}}}}}
    if accounts is not None:
        balances = [config['parity_settings']['balance'] for x in accounts]
        additional_balances = {str(x): {"balance": str(y)} for x, y in zip(accounts, balances)}
        merged_balances = {**base_balances, **additional_balances}
    else:
        merged_balances = base_balances
        accounts = []

    spec_dict = {
                 "name": "DemoPoA",
                 "engine": {
                         "authorityRound": {
                                     "params": {
                                                 "stepDuration": config['parity_settings']['step_duration'],
                                                 "validators": {
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
                 "gasLimit": config['parity_settings']['gaslimit']
                 },
                 "accounts": merged_balances
                }

    return spec_dict

class Error(Exception):
   """Base class for other exceptions"""
   pass
class ParityInstallFailed(Error):
   """Parity could not be installed"""
   pass

