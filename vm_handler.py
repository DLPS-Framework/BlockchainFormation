import sys, os, pprint
import boto3
import getpass
import pytz, time
utc = pytz.utc
from dateutil import parser
import paramiko
from scp import SCPClient
from web3 import Web3
from web3.middleware import geth_poa_middleware


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ec2_automation.cost_calculator import *
from ec2_automation.cost_calculator import AWSCostCalculator

class VM_handler:
    """
    Class for handling startup and shutdown of aws VM instances
    """

    def __init__(self, config):

        self.logger = logging.getLogger(__name__)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        self.config = config

        self.pprnt = pprint.PrettyPrinter(indent=1)

        #print("Enter proxy password:")
        password = getpass.getpass(prompt=f"Enter proxy password for {self.config['proxy_user']}:")

        os.environ["HTTPS_PROXY"] = f"http://{self.config['proxy_user']}:{password}@proxy.muc:8080"
        os.environ["HTTP_PROXY"] = f"http://{self.config['proxy_user']}:{password}@proxy.muc:8080"
        os.environ["NO_PROXY"] = "localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net"

        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = self.config['aws_credentials']
        os.environ["AWS_CONFIG_FILE"] = self.config['aws_config']

        self.user_data = self.create_user_data()

        self.session = boto3.Session(profile_name=self.config['profile'])

        self.ec2_instances = None

        self.aws_calculator = AWSCostCalculator(self.session)

    def create_user_data(self):
        """creates the user data script depending on experiment type. The user data is built out of base script and specific script depending on experiment type"""
        with open("UserDataScripts/EC2_instance_bootstrap_base.sh", 'r') as content_file:
            user_data_base = content_file.read()

        with open(f"UserDataScripts/EC2_instance_bootstrap_{self.config['blockchain_type']}.sh", 'r') as content_file:
            user_data_specific = content_file.read()

        user_data_combined = user_data_base + user_data_specific

        return user_data_combined


    def run_general_startup(self):
        """
        General startup script needed for all blockchain frameworks. After general part is finished, the specific startup script are kicked off
        :return:
        """


        def search_newest_image(list_of_images):
            """
            Search for the newest ubuntu image from a given list
            :param list_of_images: list with all found images
            :return:
            """
            latest = None
            for image in list_of_images:
                if not latest:
                    latest = image
                    continue

                if parser.parse(image['CreationDate']) > parser.parse(latest['CreationDate']):
                    latest = image

            return latest

        if self.config['image']['image_id'] == None:
            ec2 = self.session.client('ec2', region_name='eu-central-1')
            # pprnt.pprint(ec2.describe_instances())

            # Find the latest official Ubuntu image from Canonical(owner = 099720109477)
            # aws ec2 describe-images --owners 099720109477 --filters 'Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-*-18*-amd64-server-????????' 'Name=state,Values=available' --output json | jq -r '.Images | sort_by(.CreationDate) | last(.[])'

            amis = ec2.describe_images(
                Filters=[
                    {
                        'Name': 'name',
                        'Values': [f"{self.config['image']['os']}/images/hvm-ssd/{self.config['image']['os']}-*-{self.config['image']['version']}*-amd64-server-????????"]
                    },
                    {
                        'Name': 'architecture',
                        'Values': ['x86_64']
                    },
                    {
                        'Name': 'state',
                        'Values': ['available']
                    },
                    {
                        'Name': 'root-device-type',
                        'Values': ['ebs']
                    }
                ],
                Owners=[
                    '099720109477',
                ]
            )
            image = search_newest_image(amis['Images'])
            self.config['image']['image_id'] = image["ImageId"]

            # root_storage_mapping = image["BlockDeviceMappings"]
            # print([x for x in source_image["BlockDeviceMappings"]])

        ec2 = self.session.resource('ec2')
        image = ec2.Image(self.config['image']['image_id'])
        root_storage_mapping = image.block_device_mappings

        self.logger.info("Selected Image: " + image.description)

        session = boto3.Session(profile_name=self.config['profile'])
        ec2 = session.resource('ec2', region_name='eu-central-1')
        self.ec2_instances = ec2.create_instances(
            ImageId=self.config['image']['image_id'],
            MinCount=self.config['vm_count'],
            MaxCount=self.config['vm_count'],
            InstanceType=self.config['instance_type'],
            KeyName=self.config['key_name'],
            SubnetId=self.config['subnet_id'],
            BlockDeviceMappings=self.config['storage_settings'],
            UserData=self.user_data,
            TagSpecifications=[
                {
                    'ResourceType': "instance",
                    'Tags': [
                        {
                            'Key': 'Creator',
                            'Value': self.config['tag_name']
                        },
                        {
                            'Key': 'Name',
                            'Value': self.config['tag_name']
                        },
                    ]
                },
            ],
            SecurityGroupIds=self.config['security_group_id']
        )
        self.logger.info(f"Initiated the start of {self.config['vm_count']} {self.config['instance_type']} machines.")
        ips = []
        self.logger.info("Waiting until all VMs are up...")
        for i in self.ec2_instances:
            i.wait_until_running()
            i.load()
            self.logger.info(f"ID: {i.id}, State: {i.state['Name']}, IP: {i.private_ip_address}")
            ips.append(i.private_ip_address)

        # add no procy for all VM IPs
        os.environ["NO_PROXY"] = f"localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net,{','.join(str(ip) for ip in ips)}"

        self.logger.info(f"You can now access machines via: ssh -i \"path to {self.config['key_name']} key\" ubuntu@{ips} (if user is ubuntu) ")
        self.logger.info(f"e.g. ssh -i {self.config['priv_key_path']} ubuntu@{ips[0]}")

        # add instance IPs and IDs to config
        self.config['ips'] = ips
        self.config['instance_ids'] = [instance.id for instance in self.ec2_instances]

        # Give launched instances tag with time/type of experiment/number of node
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
        for index, i in enumerate(self.ec2_instances):
            exp_tag = f"exp_{st}_{self.config['blockchain_type']}_Node{index}"
            ec2.create_tags(Resources=[
                i.id,
            ],
                Tags=[
                    {
                        'Key': 'exp_tag',
                        'Value': exp_tag
                    },
                ])

        self.launch_times = []
        for i in self.ec2_instances:
            self.logger.info("Launch Time: " + str(i.launch_time))
            # get launch time
            self.launch_times.append(i.launch_time.replace(tzinfo=None))

        #create experiment directory structure
        self.config['launch_times'] = self.launch_times
        self.config['exp_dir'] = f"experiments/exp_{st}_{self.config['blockchain_type']}"
        path = os.getcwd()
        try:
            os.makedirs(f"{path}/{self.config['exp_dir']}/accounts")
            os.mkdir((f"{path}/{self.config['exp_dir']}/enodes"))
            os.mkdir((f"{path}/{self.config['exp_dir']}/geth_logs"))
            os.mkdir((f"{path}/{self.config['exp_dir']}/user_data_logs"))
        except OSError:
            self.logger.error("Creation of the directories failed")

        with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
            json.dump(self.config, outfile, default = self._datetimeconverter)

        # wait couple min until vmss are up
        # first connect ssh clients, then scp client

        self.logger.info("Waiting 60 seconds before creating ssh connection to VMs")
        time.sleep(60)
        ssh_clients, scp_clients = self.create_ssh_scp_clients()

        # convert to timedelta for nicer waiting time calcs
        status_flags = np.zeros((self.config['vm_count']), dtype=bool)
        # how many minutes to wait
        timer = 0
        self.logger.info("Waiting for all VMs to finish the userData setup...")
        while (False in status_flags and timer < 20):
            time.sleep(60)
            timer += 1
            self.logger.info(
                f"Waited {timer} minutes so far, {20 - timer} minutes left before abort (it usually takes around 10 minutes)")
            for index, i in enumerate(self.ec2_instances):

                if (status_flags[index] == False):
                    # ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("[[ -f /var/log/user_data_success.log ]] && echo 'File true' || echo 'File false'")
                    # formatted_output = ssh_stdout.read().decode("utf-8")
                    sftp = ssh_clients[index].open_sftp()
                    try:
                        sftp.stat('/var/log/user_data_success.log')
                        status_flags[index] = True
                        self.logger.info(f"{ips[index]} is ready")
                    except IOError:
                        self.logger.info(f"{ips[index]} not ready")

        if (False in status_flags):
            self.logger.error('Boot up NOT successful')
            self.logger.error(f"Failed VMs: {[ips[x] for x in np.where(status_flags != True)]}")
        else:
            self.logger.info(f"Boot up of all VMs as successful, waited {timer} minutes")

            self._run_specific_startup()

        try:
            map(lambda client: client.close(), ssh_clients)
            map(lambda client: client.close(), scp_clients)
        except:
            self.logger.info("ssh/scp clients already closed")

    def _run_specific_startup(self):
        """starts startup for given config (geth, parity, etc....)"""


        def _geth_startup():
            """
            Runs the geth specific startup script
            :return:
            """
            ssh_clients, scp_clients = self.create_ssh_scp_clients()

            for index, _ in enumerate(self.config['ips']):
                scp_clients[index].get("/data/gethNetwork/account.txt",
                                       f"{self.config['exp_dir']}/accounts/account_node_{index}.txt")
            all_accounts = []

            path = f"{self.config['exp_dir']}/accounts"
            file_list = os.listdir(path)
            #Sorting to get matching accounts to ip
            file_list.sort()
            for file in file_list:
                try:
                    file = open(os.path.join(path + "/" + file), 'r')
                    all_accounts.append(file.read())
                    file.close()
                except IsADirectoryError:
                    self.logger.debug(f"{file} is a directory")

            all_accounts = [x.rstrip() for x in all_accounts]
            self.logger.info(all_accounts)

            #create genesis json
            genesis_dict = self.generate_genesis(accounts=all_accounts,type="geth")
            #self.pprnt.pprint(genesis_dict)

            with open(f"{self.config['exp_dir']}/genesis.json", 'w') as outfile:
                json.dump(genesis_dict, outfile)

            # push genesis from local to remote VMs
            for index, _ in enumerate(self.config['ips']):
                scp_clients[index].put(f"{self.config['exp_dir']}/genesis.json", f"~/genesis.json")

            for index, _ in enumerate(self.config['ips']):
                # get account from all instances

                ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
                    "sudo mv ~/genesis.json /data/gethNetwork/genesis.json")

                self.logger.debug(ssh_stdout)
                self.logger.debug(ssh_stderr)
                ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command(
                    "sudo geth --datadir '/data/gethNetwork/node/' init /data/gethNetwork/genesis.json")
                self.logger.debug(ssh_stdout)
                self.logger.debug(ssh_stderr)

                ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("ssudo systemctl daemon-reload")
                self.logger.debug(ssh_stdout)
                self.logger.debug(ssh_stderr)

                ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl enable geth.service")
                self.logger.debug(ssh_stdout)
                self.logger.debug(ssh_stderr)

                ssh_stdin, ssh_stdout, ssh_stderr = ssh_clients[index].exec_command("sudo systemctl start geth.service")
                self.logger.debug(ssh_stdout)
                self.logger.debug(ssh_stderr)

            enodes = []
            # collect enodes
            web3_clients = []
            for index, ip in enumerate(self.config['ips']):
                #print(f"http://{ip}:8545")
                web3_clients.append(Web3(Web3.HTTPProvider(f"http://{ip}:8545")))
                # print(web3.admin)
                enodes.append((ip, web3_clients[index].admin.nodeInfo.enode))
                time.sleep(1)

            #Does sleep fix the Max retries exceeded with url?
            time.sleep(3)
            # print(enodes)
            self.logger.info([enode for (ip, enode) in enodes])

            with open(f"{self.config['exp_dir']}/static-nodes.json", 'w') as outfile:
                json.dump([enode for (ip, enode) in enodes], outfile)

            # distribute collected enodes over network
            for index, ip in enumerate(self.config['ips']):
                # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
                for ip_2, enode in enodes:
                    # dont add own enode
                    if ip != ip_2:
                        web3_clients[index].admin.addPeer(enode)

                self.logger.info(web3_clients[index].admin.peers)

            time.sleep(3)

            self.logger.info("Testing if transaction between Nodes work:")
            #TODO: move this to unit test section
            for index, i in enumerate(self.ec2_instances):
                # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
                self.logger.info("IsMining:" + str(web3_clients[index].eth.mining))
                for acc in all_accounts:
                    self.logger.info(str(web3_clients[index].toChecksumAddress(acc)) + ": " + str(
                        web3_clients[index].eth.getBalance(web3_clients[index].toChecksumAddress(acc))))

            # https://web3py.readthedocs.io/en/stable/middleware.html#geth-style-proof-of-authority

            time.sleep(15)

            try:
                web3_clients[0].middleware_stack.inject(geth_poa_middleware, layer=0)
            except:
                self.logger.info("Middleware already injected")

            self.logger.info("Tx from " + str(web3_clients[0].toChecksumAddress(all_accounts[0])) + " to " + str(
                web3_clients[0].toChecksumAddress(all_accounts[1])))
            web3_clients[0].personal.sendTransaction({'from': web3_clients[0].toChecksumAddress(all_accounts[0]),
                                                      'to': web3_clients[0].toChecksumAddress(all_accounts[1]),
                                                      'value': web3_clients[0].toWei(23456, 'ether'), 'gas': '0x5208',
                                                      'gasPrice': web3_clients[0].toWei(5, 'gwei')}, "password")
            time.sleep(30)
            for index, i in enumerate(self.ec2_instances):
                # web3 = Web3(Web3.HTTPProvider(f"http://{i.private_ip_address}:8545"))
                for acc in all_accounts:
                    self.logger.info(str(web3_clients[index].toChecksumAddress(acc)) + ": " + str(
                        web3_clients[index].eth.getBalance(web3_clients[index].toChecksumAddress(acc))))
                self.logger.info("---------------------------")

            web3_clients[0].eth.getBlock('latest')

            try:
                map(lambda client: client.close(), ssh_clients)
                map(lambda client: client.close(), scp_clients)
            except:
                self.logger.info("ssh/scp clients already closed")


        if self.config['blockchain_type'] == 'geth':
            _geth_startup()

        #TODO: differentiate between different exp types

    def run_shutdown(self):
        """
         Stops and terminates all VMs and calculates causes aws costs.
        :return:
        """
        #TODO: enable stopping and not only termination

        os.environ["NO_PROXY"] = f"localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net,{','.join(str(ip) for ip in self.config['ips'])}"

        def geth_shutdown():
            """
            runs the geth specific shutdown operations (e.g. pulling the geth logs from the VMs)
            :return:
            """
            ssh_clients, scp_clients = self.create_ssh_scp_clients()

            for index, _ in enumerate(self.config['ips']):
                # get account from all instances
                scp_clients[index].get("/var/log/geth.log",
                                       f"{self.config['exp_dir']}/geth_logs/geth_log_node_{index}.log")
                scp_clients[index].get("/var/log/user_data.log",
                                       f"{self.config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")

        geth_shutdown()

        #or i in self.ec2_instances:
         #   i.stop()
        #calculate aws costs
        ec2 = self.session.resource('ec2')
        ec2.instances.filter(InstanceIds=self.config['instance_ids']).stop()



        self.aws_calculator.calculate_uptime_costs(self.config)

        #termination_times = []
        #for i in self.ec2_instances:
           # i.terminate()
            # Note this termination is only an approximation
           # termination_times.append(datetime.datetime.utcnow())

        ec2.instances.filter(InstanceIds=self.config['instance_ids']).terminate()

        self.logger.info("All instances terminated -  script is finished")





    def create_ssh_scp_clients(self):
        """
        Creates ssh/scp connection to aws VMs

        :return: array of scp and ssh clients
        """
        ssh_clients = []
        scp_clients = []
        ssh_key_priv = paramiko.RSAKey.from_private_key_file(self.config['priv_key_path'])

        for index, ip in enumerate(self.config['ips']):
            ssh_clients.append(paramiko.SSHClient())
            ssh_clients[index].set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_clients[index].connect(hostname=ip, username=self.config['user'], pkey=ssh_key_priv)
            # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)

            # SCPCLient takes a paramiko transport as an argument
            scp_clients.append(SCPClient(ssh_clients[index].get_transport()))

        return ssh_clients, scp_clients

    def generate_genesis(self, accounts, type= "geth"):
        """
        #TODO make it more dynamic to user desires
        :param accounts: accounts to be added to signers/added some balance
        :param type: type of experiment
        :return: genesis dictonary
        """

        balances = ["0x200000000000000000000000000000000000000000000000000000000000000" for x in accounts]
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
                'chainId': 11,
                'homesteadBlock': 0,
                'eip150Block': 0,
                'eip155Block': 0,
                'eip158Block': 0,
                'byzantiumBlock': 0,
                'clique': {
                    'period': 5,
                    'epoch': 30000
                }
            },
            "alloc": merged_balances,
            "coinbase": "0x0000000000000000000000000000000000000000",
            "difficulty": "0x1",
            "extraData": f"0x0000000000000000000000000000000000000000000000000000000000000000{''.join(accounts)}0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000",
            "gasLimit": "0x2fefd8",
            "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "nonce": "0x0000000000000042",
            "timestamp": "0x00"

        }
        return genesis_dict
    def _datetimeconverter(self, o):
        """Converter to make datetime objects json dumpable"""
        if isinstance(o, datetime.datetime):
            return o.__str__()
