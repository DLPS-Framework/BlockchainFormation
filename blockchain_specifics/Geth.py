import os
import sys
import json
import re
import time
import random
import glob
import itertools
import numpy as np
from web3 import Web3
from web3.middleware import geth_poa_middleware



def geth_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the geth specific shutdown operations (e.g. pulling the geth logs from the VMs)
    :return:
    """

    for index, _ in enumerate(config['ips']):
        # get account from all instances
        scp_clients[index].get("/var/log/geth.log",
                               f"{config['exp_dir']}/geth_logs/geth_log_node_{index}.log")
        scp_clients[index].get("/var/log/user_data.log",
                               f"{config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")




def geth_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """
    acc_path = os.getcwd()
    os.mkdir(f"{acc_path}/{config['exp_dir']}/accounts")
    # enodes dir not needed anymore since enodes are saved in static-nodes file
    # os.mkdir((f"{path}/{self.config['exp_dir']}/enodes"))
    os.mkdir((f"{acc_path}/{config['exp_dir']}/geth_logs"))


    for index, _ in enumerate(config['ips']):
        scp_clients[index].get("/data/gethNetwork/account.txt",
                               f"{config['exp_dir']}/accounts/account_node_{index}.txt")
        scp_clients[index].get("/data/keystore",
                               f"{config['exp_dir']}/accounts/keystore_node_{index}", recursive=True)
    all_accounts = []

    acc_path = f"{config['exp_dir']}/accounts"
    file_list = os.listdir(acc_path)
    #Sorting to get matching accounts to ip
    file_list.sort()
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
    for index, ip in enumerate(config['ips']):

        #create service file on each machine
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            f"printf '%s\\n' '[Unit]' 'Description=Ethereum go client' '[Service]' 'Type=simple' "
            f"'ExecStart=/usr/bin/geth --datadir /data/gethNetwork/node/ --networkid 11 --verbosity 3 "
            f"--port 30310 --rpc --rpcaddr 0.0.0.0  --rpcapi db,clique,miner,eth,net,web3,personal,web3,admin,txpool"
            f" --nat=extip:{ip}  --syncmode full --unlock {','.join([Web3.toChecksumAddress(x) for x in account_mapping[ip]])} --password /data/gethNetwork/passwords.txt --mine ' 'StandardOutput=file:/var/log/geth.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/geth.service")
        #logger.debug(ssh_stdout)
        #logger.debug(ssh_stderr)
        logger.debug(ssh_stdin)

        for _, acc in enumerate(account_mapping[ip]):
            ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("echo 'password' >> /data/gethNetwork/passwords.txt")
            logger.debug(ssh_stdout)
            logger.debug(ssh_stderr)


    if config['geth_settings']['num_acc'] != None:
        #add the keyfiles from all relevant accounts to the VMs keystores

        keystore_files = [f for f in glob.glob(acc_path + "**/*/UTC--*", recursive=True) if re.match("(.*--.*--)(.*)", f).group(2) in list(set(itertools.chain(*account_mapping.values())))]
        keystore_files.sort()
        logger.info(keystore_files)
        for index_top, ip in enumerate(config['ips']):

            ssh_clients[index_top].exec_command("rm /data/gethNetwork/node/keystore/*")

            for index_lower, file in enumerate(keystore_files):
                # only add keyfile to VM if its the right account
                #if re.match("(.*--.*--)(.*)", file).group(2) in list(set(itertools.chain(*account_mapping.values()))):
                scp_clients[index_top].put(file, "/data/gethNetwork/node/keystore")


    #create genesis json
    #get unique accounts from mapping
    genesis_dict = generate_genesis(accounts=list(set(itertools.chain(*account_mapping.values()))), config=config)
    #self.pprnt.pprint(genesis_dict)

    with open(f"{config['exp_dir']}/genesis.json", 'w') as outfile:
        json.dump(genesis_dict, outfile)

    # push genesis from local to remote VMs
    for index, _ in enumerate(config['ips']):
        scp_clients[index].put(f"{config['exp_dir']}/genesis.json", f"~/genesis.json")

    for index, _ in enumerate(config['ips']):
        # get account from all instances

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo mv ~/genesis.json /data/gethNetwork/genesis.json")

        #logger.debug(ssh_stdout)
        #logger.debug(ssh_stderr)
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
            "sudo geth --datadir '/data/gethNetwork/node/' init /data/gethNetwork/genesis.json")
        #logger.debug(ssh_stdout)
        #logger.debug(ssh_stderr)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("ssudo systemctl daemon-reload")
        #logger.debug(ssh_stdout)
        #logger.debug(ssh_stderr)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl enable geth.service")
        #logger.debug(ssh_stdout)
        #logger.debug(ssh_stderr)

        ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl start geth.service")
        #logger.debug(ssh_stdout)
        #logger.debug(ssh_stderr)

    enodes = []
    # collect enodes
    web3_clients = []
    time.sleep(30)
    for index, ip in enumerate(config['ips']):
        #print(f"http://{ip}:8545")
        web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip}:8545")))
        # print(web3.admin)
        enodes.append((ip, web3_clients[index].admin.nodeInfo.enode))
        time.sleep(1)
        #web3_clients[index].miner.stop()
        #time.sleep(1)


        #add accounts to node
        #for acc in account_mapping[ip]:
            #logger.info(f"Unlocking {acc} on {ip}")
            #logger.debug(f"{acc}:{web3_clients[index].personal.unlockAccount(account=Web3.toChecksumAddress(acc), passphrase='password', duration=100000)}")
            #time.sleep(2)

        #web3_clients[index].miner.start(8)


    #Change default accounts of nodes to avoid the nodes of  getting stuck
    if config['geth_settings']['num_acc'] != None:
        i = 0
        for index, ip in enumerate(config['ips']):
            web3_clients[index].eth.defaultAccount = Web3.toChecksumAddress(account_mapping[ip][i])
            web3_clients[index].miner.setEtherBase(Web3.toChecksumAddress(account_mapping[ip][i]))
            if len(account_mapping[ip])== (i+1):
                i = 0
            else:
                i += 1
            web3_clients[index].miner.stop()
            web3_clients[index].miner.start(8)
            time.sleep(1)
            logger.info(f"Coinbase of {ip}: {web3_clients[index].eth.coinbase}")


    #Does sleep fix the Max retries exceeded with url?
    time.sleep(3)
    # print(enodes)
    logger.info([enode for (ip, enode) in enodes])

    with open(f"{config['exp_dir']}/static-nodes.json", 'w') as outfile:
        json.dump([enode for (ip, enode) in enodes], outfile)

    # distribute collected enodes over network
    for index, ip in enumerate(config['ips']):
        # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
        for ip_2, enode in enodes:
            # dont add own enode
            if ip != ip_2:
                web3_clients[index].admin.addPeer(enode)
                time.sleep(1)

        logger.info(web3_clients[index].admin.peers)

    time.sleep(3)

    logger.info("Testing if transaction between Nodes work:")
    #TODO: move this to unit test section
    for index, ip in enumerate(config['ips']):
        # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
        logger.info("IsMining:" + str(web3_clients[index].eth.mining))
        for acc in all_accounts:
            logger.info(str(web3_clients[index].toChecksumAddress(acc)) + ": " + str(
                web3_clients[index].eth.getBalance(Web3.toChecksumAddress(acc))))



    # https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority

    time.sleep(15)

    for index, _ in enumerate(config['ips']):
        try:
            web3_clients[index].middleware_stack.inject(geth_poa_middleware, layer=0)
        except:
            logger.info("Middleware already injected")
    #
    # logger.info("Tx from " + str(Web3.toChecksumAddress(all_accounts[0])) + " to " + str(
    #     Web3.toChecksumAddress(all_accounts[1])))
    # web3_clients[0].personal.sendTransaction({'from': Web3.toChecksumAddress(all_accounts[0]),
    #                                           'to': Web3.toChecksumAddress(all_accounts[1]),
    #                                           'value': web3_clients[0].toWei(23456, 'ether'), 'gas': '0x5208',
    #                                           'gasPrice': web3_clients[0].toWei(5, 'gwei')}, "password")
    # time.sleep(30)
    # for index, ip in enumerate(config['ips']):
    #     # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
    #     for acc in all_accounts:
    #         logger.info(str(Web3.toChecksumAddress(acc)) + ": " + str(
    #             web3_clients[index].eth.getBalance(Web3.toChecksumAddress(acc))))
    #     logger.info("---------------------------")

    logger.info("testing if new blocks are generated")
    for x in range(15):
        logger.info(web3_clients[0].eth.getBlock('latest')['number'])
        logger.info(web3_clients[1].eth.getBlock('latest')['number'])
        logger.info(web3_clients[2].eth.getBlock('latest')['number'])
        logger.info(web3_clients[3].eth.getBlock('latest')['number'])
        logger.info("----------------------------------")
        time.sleep(10)


def get_relevant_account_mapping(accounts, config):
    """
    returns the array with the relevant accounts for the genesis and unlock process
    :param accounts:
    :param config:
    :return:
    """

    if config['geth_settings']['num_acc'] == None:
        return {ip: [account] for (ip, account) in zip(config['ips'], accounts)}
    else:

        #return np.random.choice(a=accounts, replace=False, size=config['geth_settings']['num_acc'])
        rnd_accounts = np.random.choice(a=accounts, replace=False, size=config['geth_settings']['num_acc'])
        return {ip: rnd_accounts for ip in config['ips']}



def generate_genesis(accounts, config):
    """
    #TODO make it more dynamic to user desires
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
        "extraData": f"0x0000000000000000000000000000000000000000000000000000000000000000{''.join(accounts)}0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
        "gasLimit": config['geth_settings']['gaslimit'],
        "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        "nonce": "0x0000000000000042",
        "timestamp": config['geth_settings']['timestamp']

    }
    return genesis_dict
