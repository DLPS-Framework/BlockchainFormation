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



import sys, os, argparse
import json
import datetime, time
import logging.config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from BlockchainFormation.vm_handler import VMHandler


class ArgParser:

    def __init__(self):
        """Initialize an ArgParser object.
        The general structure of calls from the command line is:

        """

        self.parser = argparse.ArgumentParser(description='This script automizes setup for various blockchain networks on aws and calculates aws costs after finshing'\
                                    , usage = 'run.py start geth --vm_count 4 --instance_type t2.micro  --priv_key_path ~/.ssh/blockchain --tag_name blockchain_test --subnet_id subnet-345 --security_group_id sg-345 '
                                             'run.py terminate --config /home/config.json')

        subparsers_start_terminate = self.parser.add_subparsers(help='start instances or terminate them')

        parser_start = subparsers_start_terminate.add_parser('start', help='startup')
        parser_termination = subparsers_start_terminate.add_parser('terminate', help='termination')

        parser_start.set_defaults(goal='start')
        parser_start.add_argument('--config', '-c', help='enter path to config file')

        ArgParser._add_blockchain_subparsers(parser_start)

        parser_termination.add_argument('--config', '-c', help='enter path to config file')
        parser_termination.set_defaults(goal='termination')

    @staticmethod
    def _add_blockchain_subparsers(superparser):
        """
        Add subparsers to a superparser, with arguments depending on the goal.
        :param superparser: The parser to which to add subparsers.
        :return:
        """

        subparsers = superparser.add_subparsers(help='Choose a blockchain type')

        # fabric parser
        parser_fabric = subparsers.add_parser('fabric', help='Fabric Network')
        parser_fabric.set_defaults(blockchain_type='fabric')
        ArgParser._add_common_args(parser_fabric)
        ArgParser._add_fabric_args(parser_fabric)

        # geth parser
        parser_geth = subparsers.add_parser('geth', help='Geth Network')
        parser_geth.set_defaults(blockchain_type='geth')
        ArgParser._add_common_args(parser_geth)
        ArgParser._add_loadbalancer_args(parser_geth)
        ArgParser._add_geth_args(parser_geth)

        # parity parser
        parser_parity = subparsers.add_parser('parity', help='Parity Network')
        parser_parity.set_defaults(blockchain_type='parity')
        ArgParser._add_common_args(parser_parity)
        ArgParser._add_loadbalancer_args(parser_parity)
        ArgParser._add_parity_args(parser_parity)

        # quorum parser
        parser_quorum = subparsers.add_parser('quorum', help='Quorum Network')
        parser_quorum.set_defaults(blockchain_type='quorum')
        ArgParser._add_common_args(parser_quorum)
        ArgParser._add_quorum_args(parser_quorum)

        # sawtooth parser
        parser_sawtooth = subparsers.add_parser('sawtooth', help='Sawtooth Network')
        parser_sawtooth.set_defaults(blockchain_type='sawtooth')
        ArgParser._add_common_args(parser_sawtooth)
        ArgParser._add_sawtooth_args(parser_sawtooth)

        # client parser
        parser_client = subparsers.add_parser('client', help='Set up Clients')
        parser_client.set_defaults(blockchain_type='client')
        ArgParser._add_common_args(parser_client)
        ArgParser._add_client_args(parser_client)

        # base parser
        parser_base = subparsers.add_parser('base',
                                            help='Base Setup, only starts VM & installs basic packages, no blockchain')
        parser_base.set_defaults(blockchain_type='base')
        ArgParser._add_common_args(parser_base)
        ArgParser._add_loadbalancer_args(parser_base)
        # base does no need any specific args


    @staticmethod
    def _add_loadbalancer_args(parser):
        """
        Add args needed to configure the loadbalancer
        :return:
        """

        parser.add_argument('--add_loadbalancer', '-add_lb',
                            help='True or False whether you want a application load balancer',
                            default=False, type=bool)
        parser.add_argument('--lb_subnet_ids', '-lb_st',
                            help='load balancer subnet ids (at least two from different availability zones)', default=['subnet-123','subnet-234'], nargs='+')
        parser.add_argument('--lb_security_group_ids', '-lb_sg',
                            help='security group, multiple values allowed', default=["sg-123123"], nargs='+')
        parser.add_argument('--lb_port', '-lb_p', help='which port should load balancer listen AND hit', type=int, default=8545)
        parser.add_argument('--lb_hosted_zone_id', '-hzi',
                            help='hosted zone id for route 53', default='iuiuiut')



    @staticmethod
    def storage_type(x):
        """Check if the chosen storage is in a given range (Needs to be >1 else the mounting process of the UserData
        script fails)"""
        x = int(x)
        if x < 9 or x > 2048:
            raise argparse.ArgumentTypeError("Minimum storage is 9GB, maximum is 1024 GB")
        return x

    @staticmethod
    def _add_common_args(parser):
        """
        Add common arguments to a (sub-)parser. Used instead of specifying parents for the subparsers (for design reasons).
        :param parser: The parser to which to add the arguments.
        :return:
        """

        parser.add_argument('--vm_count', '-vmc', help='specify how many VM you want to start', type=int)
        parser.add_argument('--instance_type', '-it', help='specify what type of instances you want to start',
                                 default='t2.micro', choices=['t2.nano','t2.micro','t2.small','t2.medium','t2.large', 't2.xlarge','t2.2xlarge','m5.large','m5.xlarge','m5.2xlarge','m5.8xlarge'])
        parser.add_argument('--aws_credentials', '-cred',
                                 help='path to aws credentials', default=os.path.expanduser('~/.aws/credentials'))
        parser.add_argument('--key_name', '-kn',
                                       help='name of aws credentials key', default="blockchain")
        parser.add_argument('--aws_config', '-aws_con',
                                 help='path to aws config', default=os.path.expanduser('~/.aws/config'))
        parser.add_argument('--aws_region', '-aws_r',
                            help='aws region where images should be hosted', default='eu-central-1')
        parser.add_argument('--aws_http_proxy', '-aws_http_proxy',
                            help='aws http proxy (only needed for private VPCs)', default=None)
        parser.add_argument('--aws_https_proxy', '-aws_https_proxy',
                            help='aws https proxy (only needed for private VPCs)',
                            default=None)
        parser.add_argument('--aws_no_proxy', '-aws_no_proxy',
                            help='aws no proxy (only needed for private VPCs)',
                            default='localhost,127.0.0.1')
        parser.add_argument('--priv_key_path', '-key',
                                 help='path to  ssh key', default=os.path.expanduser('~/.ssh/blockchain'))
        parser.add_argument('--image_id', '-img_id',
                                       help='image ID for vm (default is to get newest ubuntu 18 build)', default=None)
        parser.add_argument('--image_version', '-img_v',
                            help='ubuntu version (default = 18)', default=18, type=int)
        parser.add_argument('--VolumeSize', '-s',
                                 help='amount of VolumeSize in GB: min 8, max 1024', type=ArgParser.storage_type, default=32)
        parser.add_argument('--KmsKeyId', '-KId',
                                 help='KmsKeyId for Encryption, None for no Encryption', default=None)
        parser.add_argument('--profile', '-p',
                                 help='name of aws profile, None for no profile switching', default='block_exp')
        parser.add_argument('--tag_name', '-t',
                                 help='tag for aws', default='blockchain_experiment')
        parser.add_argument('--subnet_id', '-st',
                                 help='subnet id', default='subnet-123')
        parser.add_argument('--security_group_id', '-sg',
                                 help='security group, multiple values allowed', default=["sg-123"],nargs='+')
        parser.add_argument('--public_ip', '-pub_ip',
                            help='True or False if public IP is needed (remember to define correct subnet/security))', default=False, type=bool)
        parser.add_argument('--proxy_user', '-pu',
                                 help='proxy user; None for NO proxy ', default=None)
        parser.add_argument('--http_proxy', '-http_proxy',
                            help='HTTP proxy url and port ', default=None)
        parser.add_argument('--https_proxy', '-https_proxy',
                            help='HTTPS proxy url and port ', default=None)
        parser.add_argument('--no_proxy', '-no_proxy',
                            help='NO PROXY', default=None)
        parser.add_argument('--exp_dir', '-exp_d',
                            help='Directory where experiment folder is created (default=os.getcwd())', default=os.getcwd())
        parser.add_argument('--aws_spot_instances',
                            help='Boolean if spot instances should be used for aws', default=False, type=bool)



    @staticmethod
    def _add_fabric_args(parser):
        parser.add_argument('--org_count', help='specify number of organizations', type=int, default=2)
        parser.add_argument('--peer_count', help='specify number of peers per organization', type=int, default=3)
        parser.add_argument('--orderer_type', help='specify the orderer type chosen from "solo" and "raft", default="solo"')
        parser.add_argument('--orderer_count', help='specify number of orderers - if orderer_type is "solo", then orderer_count must be 1', type=int, default=1)
        parser.add_argument('--kafka_count', help='specify number of kafka nodes - only relevant if orderer_type is kafka', type=int, default=3)
        parser.add_argument('--zookeeper_count', help='specify number of zookeepers - only relevant if orderer_type is kafka', type=int, default=5)
        parser.add_argument('--batch_timeout', help='specify the amount of seconds to wait before creating a batch',
                            type=int, default=2)
        parser.add_argument('--max_message_count', help='specify the maximum number of messages to permit in a batch',
                            type=int, default=10)
        parser.add_argument('--absolute_max_bytes',
                            help='specify the absolute maximum number of MB allowed for the serialized messages in a batch',
                            type=int, default=99)
        parser.add_argument('--preferred_max_bytes',
                            help='specify the preferred maximum number of KB allowed for the serialized messages in a batch',
                            type=int, default=512)
        parser.add_argument('--tls_enabled',
                            help='specify whether communication in the network is encrypted; chosse between 0 (tls disables) and 1 (tls enabled)',
                            type=int, default=1)
        parser.add_argument('--endorsement_policy',
                            help='specify the endorsement policy for the benchmarking test; choose between "AND" and "OR" (currently two organizations), default="OR"')
        parser.add_argument('--log_level',
                            help='the logging severity levels are specified using case-insensitive strings chosen from << FATAL | PANIC | ERROR | WARNING | INFO | DEBUG >>',
                            default="debug")

    @staticmethod
    def _add_geth_args(parser):
        # https://github.com/ethereum/go-ethereum/wiki/Command-Line-Options
        parser.add_argument('--chainid', '-ci', help='specify chainID', type=int, default=11)
        parser.add_argument('--period', '-pd', help='specify clique period', type=int, default=5)
        parser.add_argument('--epoch', '-eh', help='specify clique epoch', type=int, default=30000)
        parser.add_argument('--balance', '-bal', help='specify start balance of account', default="0x200000000000000000000000000000000000000000000000000000000000000")
        parser.add_argument('--timestamp', '-tp', help='specify timestamp of genesis', default="0x00")
        parser.add_argument('--gaslimit', '-gl', help='specify gasLimit', default="0x2fefd8")
        parser.add_argument('--num_acc', '-na', help='specify number of accounts added to each node', type=int, default=None)
        parser.add_argument('--cache', help='megabytes of memory allocated to internal caching', type=int, default=1024)
        parser.add_argument('--cache.database', help='percentage of cache memory allowance to use for database io',
                            type=int, default=75)
        parser.add_argument('--cache.gc', help='percentage of cache memory allowance to use for trie pruning', type=int,
                            default=25)
        #parser.add_argument('--trie-cache-gens', help='number of trie node generations to keep in memory', type=int,
            #                default=120)
        parser.add_argument('--txpool.rejournal', help='time interval to regenerate the local transaction journal',
                            default='1h0m0s')
        parser.add_argument('--txpool.accountslots',
                            help='minimum number of executable transaction slots guaranteed per account', type=int,
                            default=16)
        parser.add_argument('--txpool.globalslots',
                            help='maximum number of executable transaction slots for all accounts', type=int,
                            default=4096)
        parser.add_argument('--txpool.accountqueue',
                            help='maximum number of non-executable transaction slots permitted per account', type=int,
                            default=64)
        parser.add_argument('--txpool.globalqueue',
                            help='maximum number of non-executable transaction slots for all accounts', type=int,
                            default=1024)
        parser.add_argument('--txpool.lifetime', help='maximum amount of time non-executable transaction are queued',
                            default='3h0m0s')
        parser.add_argument('--minerthreads',
                            help=' Number of CPU threads to use for mining (default: 8)',
                            type=int, default=8)
        parser.add_argument('--signers',
                            help='Percentage of nodes who are signers (default: 1.0)',
                            type=float, default=1.0)

    @staticmethod
    def _add_parity_args(parser):
        parser.add_argument('--step_duration', '-sd', help='specify step_duration', type=int, default=5)
        parser.add_argument('--num_acc', '-na', help='specify number of accounts added to each node', type=int,
                            default=None)
        parser.add_argument('--gaslimit', '-gl', help='specify gasLimit', default="0x5B8D80")
        parser.add_argument('--balance', '-bal', help='specify start balance of account', default="0x200000000000000000000000000000000000000000000000000000000000000")
        parser.add_argument('--tx_queue_mem_limit',
                            help='Maximum amount of memory that can be used by the transaction queue. Setting this parameter to 0 disables limiting. (default: 4)', type=int, default=4)
        parser.add_argument('--tx_queue_size',
                            help='Maximum amount of transactions in the queue (waiting tobe included in next block). (default: 8192)', type=int, default=8192)
        parser.add_argument('--cache_size_db',
                            help='Override database cache size. (default: 128)', type=int, default=128)
        parser.add_argument('--cache_size_blocks',
                            help='Specify the preferred size of the blockchain cache in megabytes. (default: 8)', type=int, default=8)
        parser.add_argument('--cache_size_queue',
                            help='Specify the maximum size of memory to use for blockqueue. (default: 40)', type=int, default=40)
        parser.add_argument('--cache_size_state',
                            help='Specify the maximum size of memory to use for the statecache. (default: 25)', type=int, default=25)
        parser.add_argument('--server_threads',
                            help='RPC server threads (default: 4)',
                            type=int, default=4)
        parser.add_argument('--signers',
                            help='Percentage of nodes who are signers (default: 1.0)',
                            type=float, default=1.0)

    @staticmethod
    def _add_quorum_args(parser):
        parser.add_argument('--raftblocktime', help='amount of time between raft block creations in milliseconds', type=int, default=50)
        parser.add_argument('--cache', help='megabytes of memory allocated to internal caching', type=int, default=1024)
        parser.add_argument('--cache.database', help='percentage of cache memory allowance to use for database io', type=int, default=75)
        parser.add_argument('--cache.gc', help='percentage of cache memory allowance to use for trie pruning', type=int, default=25)
        # parser.add_argument('--trie-cache-gens', help='number of trie node generations to keep in memory', type=int, default=120)
        parser.add_argument('--txpool.rejournal', help='time interval to regenerate the local transaction journal', default='1h0m0s')
        parser.add_argument('--txpool.accountslots', help='minimum number of executable transaction slots guaranteed per account', type=int, default=16)
        parser.add_argument('--txpool.globalslots', help='maximum number of executable transaction slots for all accounts', type=int, default=4096)
        parser.add_argument('--txpool.accountqueue', help='maximum number of non-executable transaction slots permitted per account', type=int, default=64)
        parser.add_argument('--txpool.globalqueue', help='maximum number of non-executable transaction slots for all accounts', type=int, default=1024)
        parser.add_argument('--txpool.lifetime', help='maximum amount of time non-executable transaction are queued', default='3h0m0s')
        parser.add_argument('--private_fors', help='number of recipients for private transactions (at most one less than tessera nodes)', default="all")

    @staticmethod
    def _add_sawtooth_args(parser):
        pass

    @staticmethod
    def _add_client_args(parser):
        parser.add_argument('--target_network_conf', '-gl', help='Config where client IPs are attached to', default=None)

    def create_config(self, namespace_dict, blockchain_type):
        """
        Crates config for vm handler for a given namespace provided by argpass CLI
        :param blockchain_type: type of blockchain that should be created
        :param namespace_dict: namespace containing the config informations
        :return: config for vm handler
        """
        config = {
            "timestamp": datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H-%M'),
            "vm_count": namespace_dict['vm_count'],
            "instance_type": namespace_dict['instance_type'],
            "image": {
                "image_id": namespace_dict['image_id'],
                "os": "ubuntu",
                "version": namespace_dict['image_version'],
                "permissions": "default"
            },
            "subnet_id": namespace_dict['subnet_id'],
            "security_group_id": namespace_dict['security_group_id'],
            "proxy": ArgParser._add_proxy_settings(namespace_dict),
            "user": "ubuntu",
            "profile": namespace_dict['profile'],
            "key_name": namespace_dict['key_name'],
            "aws_credentials": os.path.expanduser(namespace_dict['aws_credentials']),
            "aws_config": os.path.expanduser(namespace_dict['aws_config']),
            "aws_region": namespace_dict['aws_region'],
            "aws_proxy_settings": ArgParser._add_aws_proxy_settings(namespace_dict),
            "aws_spot_instances": namespace_dict['aws_spot_instances'],
            "priv_key_path": os.path.expanduser(namespace_dict['priv_key_path']),
            "public_ip": namespace_dict['public_ip'],
            "tag_name": namespace_dict['tag_name'],
            "exp_dir": namespace_dict["exp_dir"],
            "storage_settings": [
                {
                    'DeviceName': "/dev/sdb",
                    'VirtualName': 'string',
                    'Ebs': ArgParser._add_ebs_settings(namespace_dict),
                },
            ],
            "blockchain_type": blockchain_type,
            f"{blockchain_type}_settings": ArgParser._add_blockchain_type_config(namespace_dict, blockchain_type),
            "load_balancer_settings": ArgParser._add_load_balancer_config(namespace_dict)

        }

        return config

    @staticmethod
    def _add_ebs_settings(namespace_dict):
        """
        Creates storage ebs settings
        :param namespace_dict: namespace given by the Argpass CLI
        :return: ebs dict
        """
        if namespace_dict['KmsKeyId'] == "None":
            return {
                        'DeleteOnTermination': True,
                        'VolumeSize': namespace_dict['VolumeSize'],
                        'VolumeType': 'gp2',
                        'Encrypted': False
                    }
        else:
            return {
                'DeleteOnTermination': True,
                'VolumeSize': namespace_dict['VolumeSize'],
                'VolumeType': 'gp2',
                'Encrypted': True,
                'KmsKeyId': namespace_dict['KmsKeyId']
                    }

    @staticmethod
    def _add_aws_proxy_settings(namespace_dict):
        """
        Creates aws proxy settings
        :param namespace_dict: namespace given by the Argpass CLI
        :return: aws proxy dict
        """
        if 'aws_http_proxy' in namespace_dict and namespace_dict['aws_http_proxy']:
            return \
                {
                    "aws_http_proxy": namespace_dict['aws_http_proxy'],
                    "aws_https_proxy": namespace_dict['aws_https_proxy'],
                    "aws_no_proxy": namespace_dict['aws_no_proxy']
                }
        else:
            return None

    @staticmethod
    def _add_proxy_settings(namespace_dict):
        """
        Creates proxy settings for the python script, sometimes proxy is needed if you are behind e.g. corporate proxy
        :param namespace_dict: namespace given by the Argpass CLI
        :return: proxy dict
        """

        if 'http_proxy' in namespace_dict and namespace_dict['http_proxy']:
            return \
                {
                    "proxy_user": namespace_dict['proxy_user'] if 'proxy_user' in namespace_dict else None,
                    "http_proxy": namespace_dict['http_proxy'],
                    "https_proxy": namespace_dict['https_proxy'],
                    "no_proxy": namespace_dict['no_proxy']
                }
        else:
            return None


    @staticmethod
    def _add_load_balancer_config(namespace_dict):


        if 'add_loadbalancer' in namespace_dict and namespace_dict['add_loadbalancer']:
            return \
                {
                    "add_loadbalancer": namespace_dict['add_loadbalancer'],
                    "lb_subnet_ids": namespace_dict['lb_subnet_ids'],
                    "lb_security_group_ids": namespace_dict['lb_security_group_ids'],
                    "lb_port": namespace_dict['lb_port'],
                    "lb_hosted_zone_id": namespace_dict['lb_hosted_zone_id']
                }
        else:
            return \
                {
                    "add_loadbalancer": False
                }

    @staticmethod
    def _add_blockchain_type_config(namespace_dict, blockchain_type):

        if blockchain_type == "fabric":
            return\
                {
                    "org_count": namespace_dict['org_count'],
                    "peer_count": namespace_dict['peer_count'],
                    "orderer_type": namespace_dict['orderer_type'],
                    "orderer_count": namespace_dict['orderer_count'],
                    "kafka_count": namespace_dict['kafka_count'],
                    "zookeeper_count": namespace_dict['zookeeper_count'],
                    "tick_interval": namespace_dict['tick_interval'],
                    "election_tick": namespace_dict['election_tick'],
                    "heartbeat_tick": namespace_dict['heartbeat_tick'],
                    "max_inflight_locks": namespace_dict['max_inflight_locks'],
                    "snapshot_interval_size": namespace_dict['max_inflight_locks'],
                    "batch_timeout": namespace_dict['batch_timeout'],
                    "max_message_count": namespace_dict['max_message_count'],
                    "absolute_max_bytes": namespace_dict['absolute_max_bytes'],
                    "preferred_max_bytes": namespace_dict['preferred_max_bytes'],
                    "tls_enabled": namespace_dict['tls_enabled'],
                    "endorsement_policy": namespace_dict['endorsement_policy'],
                    "log_level": namespace_dict['log_level']

                }

        elif blockchain_type == "geth":
            return\
                {
                    "chain_id": namespace_dict['chainid'],
                    "period": namespace_dict['period'],
                    "epoch": namespace_dict['epoch'],
                    "balance": namespace_dict['balance'],
                    "timestamp": namespace_dict['timestamp'],
                    "gaslimit": namespace_dict['gaslimit'],
                    "num_acc": namespace_dict['num_acc'],
                    #https://github.com/ethereum/go-ethereum/wiki/Command-Line-Options
                    "cache": namespace_dict['cache'],
                    "cache.database": namespace_dict['cache.database'],
                    "cache.gc": namespace_dict['cache.gc'],
                    #"trie-cache-gens": namespace_dict['trie-cache-gens'],
                    "txpool.rejournal": namespace_dict['txpool.rejournal'],
                    "txpool.accountslots": namespace_dict['txpool.accountslots'],
                    "txpool.globalslots": namespace_dict['txpool.globalslots'],
                    "txpool.accountqueue": namespace_dict['txpool.accountqueue'],
                    "txpool.globalqueue": namespace_dict['txpool.globalqueue'],
                    "txpool.lifetime": namespace_dict['txpool.lifetime'],
                    "minerthreads": namespace_dict['minerthreads'],
                    "signers": namespace_dict['signers']

                }
        elif blockchain_type == "parity":
            return\
                {
                    "step_duration": namespace_dict['step_duration'],
                    "num_acc": namespace_dict['num_acc'],
                    "gaslimit": namespace_dict['gaslimit'],
                    "balance": namespace_dict['balance'],
                    "server_threads": namespace_dict['server_threads'],
                    "tx_queue_mem_limit": namespace_dict['tx_queue_mem_limit'],
                    "tx_queue_size": namespace_dict['tx_queue_size'],
                    "cache_size_db": namespace_dict['cache_size_db'],
                    "cache_size_blocks": namespace_dict['cache_size_blocks'],
                    "cache_size_queue": namespace_dict['cache_size_queue'],
                    "cache_size_state": namespace_dict['cache_size_state'],
                    "signers": namespace_dict['signers']

                }
        elif blockchain_type == "quorum":
            return\
                {
                    "raftblocktime": namespace_dict['raftblocktime'],
                    "cache": namespace_dict['cache'],
                    "cache.database": namespace_dict['cache.database'],
                    "cache.gc": namespace_dict['cache.gc'],
                    "trie-cache-gens": namespace_dict['trie-cache-gens'],
                    "txpool.rejournal": namespace_dict['txpool.rejournal'],
                    "txpool.accountslots": namespace_dict['txpool.accountslots'],
                    "txpool.globalslots": namespace_dict['txpool.globalslots'],
                    "txpool.accountqueue": namespace_dict['txpool.accountqueue'],
                    "txpool.globalqueue": namespace_dict['txpool.globalqueue'],
                    "txpool.lifetime": namespace_dict['txpool.lifetime'],
                    "private_fors": namespace_dict['private_fors']

                }
        elif blockchain_type =="client":
            return\
                {
                    "target_network_conf": namespace_dict["target_network_conf"]

                }
        elif blockchain_type == "sawtooth":
            return\
                {
                    "sawtooth.consensus.algorithm.name": namespace_dict["sawtooth.consensus.algorithm.name"],
                    "sawtooth.poet.initial_wait_time": namespace_dict["sawtooth.poet.initial_wait_time"],
                    "sawtooth.poet.target_wait_time": namespace_dict["sawtooth.poet.target_wait_time"],
                    "sawtooth.publisher.max_batches_per_block": namespace_dict["sawtooth.publisher.max_batches_per_block"]
                }

    def load_config(self, namespace_dict):
        """
        Loads the config from a given JSON file
        :param namespace_dict: namespace dict containing the config file path
        :return: config dict
        """
        if namespace_dict['config'].endswith('.json'):
            try:
                with open(namespace_dict['config']) as json_file:
                    return json.load(json_file)
            except:
                logger.error("ERROR: Problem loading the given config file")
        else:
            logger.exception("Config file needs to be of type JSON")
            raise Exception("Config file needs to be of type JSON")



if __name__ == '__main__':
    argparser = ArgParser()
    namespace = argparser.parser.parse_args()

    logging.basicConfig(filename='logger.log', level=logging.DEBUG, format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')

    # BlockchainFormation: https://docs.python.org/3/howto/logging-cookbook.html
    # create logger with
    logger = logging.getLogger(__name__)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    if namespace.goal == 'start':

        # if no config file is given, a config file is created with the passed argpass commands
        if namespace.config is not None:
            # TODO check why the first does not work
            # logger.info(f"Given config file ({namespace.config}) will be used")
            logger.info("Given config file will be used")
            config = argparser.load_config(vars(namespace))
        else:
            config = argparser.create_config(vars(namespace), namespace.blockchain_type)

        vm_handler = VMHandler(config)
        vm_handler.run_general_startup()

    elif namespace.goal == 'termination':
        config = argparser.load_config(vars(namespace))
        vm_handler = VMHandler(config)
        vm_handler.run_general_shutdown()
