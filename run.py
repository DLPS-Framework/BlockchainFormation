import sys, os, argparse
import json
import logging
import logging.config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ec2_automation.vm_handler import VM_handler


class ArgParser:

    def __init__(self):
        """Initialize an ArgParser object.
        The general structure of calls from the command line is:

        run.py start --vm_count 4 --instance_type t2.micro --blockchain_type geth --ssh_key ~/.ssh/blockchain --tag blockchain_philipp --subnet subnet-0ac7aeeec87150dd7 --security_group sg-0db312b6f84d66889
        run.py terminate --config /Users/q481264/PycharmProjects/scripts/ec2_automation/experiments/exp_2019-05-13_11-20-50_geth/config.json

        """

        self.parser = argparse.ArgumentParser(description='This script automizes setup for various blockchain networks on aws and calculates aws costs after finshing'\
                                    ,usage = 'run.py start geth --vm_count 4 --instance_type t2.micro  --ssh_key ~/.ssh/blockchain --tag blockchain_philipp --subnet subnet-0ac7aeeec87150dd7 --security_group sg-0db312b6f84d66889 '
                                             'run.py terminate --config /Users/q481264/PycharmProjects/scripts/ec2_automation/experiments/exp_2019-05-13_16-32-49_geth/config.json')

        subparsers_start_terminate = self.parser.add_subparsers(help='start instances or terminate them')

        parser_start = subparsers_start_terminate.add_parser('start', help='startup')
        parser_termination = subparsers_start_terminate.add_parser('terminate', help='termination')

        parser_start.set_defaults(goal='start')

        ArgParser._add_blockchain_subparsers(parser_start)

        parser_termination.add_argument('--config', '-c', help='enter path to config')
        parser_termination.set_defaults(goal='termination')

    @staticmethod
    def _add_blockchain_subparsers(superparser):
        """
        Add subparsers to a superparser, with arguments depending on the goal.
        :param superparser: The parser to which to add subparsers.
        :return:
        """

        subparsers = superparser.add_subparsers(help='Choose a blockchain type')

        # geth parser
        parser_geth = subparsers.add_parser('geth', help='Geth Network')
        parser_geth.set_defaults(blockchain_type='geth')
        ArgParser._add_common_args(parser_geth)
        ArgParser._add_geth_args(parser_geth)

    @staticmethod
    def storage_type(x):
        x = int(x)
        if x < 8 or x > 1024:
            raise argparse.ArgumentTypeError("Minimum storage is 8GB, maximum is 1024 GB")
        return x

    @staticmethod
    def _add_common_args(parser):
        """
        Add common arguments to a (sub-)parser. Used instead of specifying parents for the subparsers (for design reasons).
        :param parser: The parser to which to add the arguments.
        :return:
        """
        parser.add_argument('--vm_count', '-vmc', help='specify how many VM you want to start', type=int)
        parser.add_argument('--instance_type', '-it',help='specify what type of instances you want to start',
                                 default='t2.micro', choices=['t2.nano','t2.micro','t2.small','t2.medium','t2.large', 't2.xlarge','t2.2xlarge'])
        #parser.add_argument('--blockchain_type', '-bt',
         #                        help='which network to setup', default='geth', choices=['geth'])
        parser.add_argument('--aws_credentials', '-cred',
                                 help='path to aws credentials', default=os.path.expanduser('~/.aws/credentials'))
        parser.add_argument('--key_name', '-kn',
                                       help='name of aws credentials key', default="blockchain")
        parser.add_argument('--aws_config', '-aws_con',
                                 help='path to aws config', default=os.path.expanduser('~/.aws/config'))
        parser.add_argument('--ssh_key', '-key',
                                 help='path to  ssh key', default=os.path.expanduser('~/.ssh/blockchain'))
        parser.add_argument('--image_id', '-img_id',
                                       help='image ID for vm (default is to get newest ubuntu 18 build)', default=None)
        parser.add_argument('--storage', '-s',
                                 help='amount of extra storage in GB: min 8, max 1024', type=ArgParser.storage_type, default=32)
        parser.add_argument('--profile', '-p',
                                 help='name of aws profile', default='block_exp')
        parser.add_argument('--tag', '-t',
                                 help='tag for aws', default='blockchain_experiment')
        parser.add_argument('--subnet', '-st',
                                 help='subnet id', default='subnet-0ac7aeeec87150dd7')
        parser.add_argument('--security_group', '-sg',
                                 help='security group, multiple values allowed', default=["sg-0db312b6f84d66889"],nargs='+')
        parser.add_argument('--proxy_user', '-pu',
                                 help='enter q number for proxy ', default='qqdpoc0')



    @staticmethod
    def _add_geth_args(parser):
        parser.add_argument('--chainid', '-ci', help='specify chainID', type=int, default=11)
        parser.add_argument('--period', '-pd', help='specify clique period', type=int, default=5)
        parser.add_argument('--epoch', '-eh', help='specify clique epoch', type=int, default=30000)
        parser.add_argument('--balance', '-bal', help='specify start balance of account', default="0x200000000000000000000000000000000000000000000000000000000000000")
        parser.add_argument('--timestamp', '-tp', help='specify timestamp of genesis', default="0x00")
        parser.add_argument('--gaslimit', '-gl', help='specify gasLimit', default="0x2fefd8")

    def create_config(self, namespace_dict, blockchain_type):
        """
        Crates config for vm handler for a given namespace provided by argpass CLI
        :param namespace_dict: namespace containing the config informations
        :return: config for vm handler
        """
        config = {
            "vm_count": namespace_dict['vm_count'],
            "instance_type": namespace_dict['instance_type'],
            "image": {
                "image_id": None,
                "os": "ubuntu",
                "version": 18,
                "permissions": "default"
            },
            "subnet_id": namespace_dict['subnet'],
            "security_group_id": namespace_dict['security_group'],
            "proxy_user": namespace_dict['proxy_user'],
            "user": "ubuntu",
            "profile": namespace_dict['profile'],
            "key_name": namespace_dict['key_name'],
            "aws_credentials": os.path.expanduser(namespace_dict['aws_credentials']),
            "aws_config": os.path.expanduser(namespace_dict['aws_config']),
            "priv_key_path": os.path.expanduser(namespace_dict['ssh_key']),
            "tag_name": namespace_dict['tag'],
            "user_data_script": "UserDataScripts/EC2_instance_bootstrap_geth.sh",
            "storage_settings": [
                {
                    'DeviceName': "/dev/sdb",
                    'VirtualName': 'string',
                    'Ebs': {
                        'DeleteOnTermination': True,
                        'VolumeSize': namespace_dict['storage'],
                        'VolumeType': 'gp2',
                        'Encrypted': True,
                        'KmsKeyId': 'arn:aws:kms:eu-central-1:731899578576:key/a808826d-e460-4271-a23b-29e1e0807c1d'
                    },
                },
            ],
            "blockchain_type": blockchain_type,
            f"{blockchain_type}_settings": ArgParser._add_blockchain_type_config(namespace_dict, blockchain_type)

        }
        return config

    @staticmethod
    def _add_blockchain_type_config(namespace_dict, blockchain_type):

        if blockchain_type == "geth":
            return\
            {
                "chain_id": namespace_dict['chainid'],
                "period": namespace_dict['period'],
                "epoch": namespace_dict['epoch'],
                "balance": namespace_dict['balance'],
                "timestamp": namespace_dict['timestamp'],
                "gaslimit": namespace_dict['gaslimit']

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

    logging.basicConfig(filename='ec2_automation.log', level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    #src: https://docs.python.org/3/howto/logging-cookbook.html
    # create logger with
    logger = logging.getLogger(__name__)
    #logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    #fh = logging.FileHandler('ec2_automation.log')
    #fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    #fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    #logger.addHandler(fh)
    logger.addHandler(ch)



    if namespace.goal == 'start':
        config = argparser.create_config(vars(namespace), namespace.blockchain_type)
        vm_handler = VM_handler(config)
        vm_handler.run_general_startup()

    elif namespace.goal == 'termination':
        config = argparser.load_config(vars(namespace))
        vm_handler = VM_handler(config)
        vm_handler.run_shutdown()
