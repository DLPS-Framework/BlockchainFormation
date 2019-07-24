import sys, os, pprint
import getpass
import pytz
from dateutil import parser
import paramiko
from scp import SCPClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from BlockchainFormation.cost_calculator import AWSCostCalculator
from BlockchainFormation.blockchain_specifics.Fabric.Fabric import *
from BlockchainFormation.blockchain_specifics.Geth.Geth import *
from BlockchainFormation.blockchain_specifics.Parity.Parity import *
from BlockchainFormation.blockchain_specifics.Quorum.Quorum import *
from BlockchainFormation.blockchain_specifics.Sawtooth.Sawtooth import *
from BlockchainFormation.blockchain_specifics.Client.Client import *
from BlockchainFormation.lb_handler import *

utc = pytz.utc

class VMHandler:
    """
    Class for handling startup and shutdown of aws VM instances
    """

    def __init__(self, config):

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
            # fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        self.config = config

        self.pprnt = pprint.PrettyPrinter(indent=1)



        # no proxy if no proxy user
        # TODO: check if "HTTP_PROXY" not in os.environ is failsafe
        if self.config['proxy_user'] != "None" and "HTTP_PROXY" not in os.environ:

            password = getpass.getpass(prompt=f"Enter proxy password for {self.config['proxy_user']}:")
            os.environ["HTTPS_PROXY"] = f"http://{self.config['proxy_user']}:{password}@proxy.muc:8080"
            os.environ["HTTP_PROXY"] = f"http://{self.config['proxy_user']}:{password}@proxy.muc:8080"
            os.environ["NO_PROXY"] = "localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net"
        else:
            self.logger.info("No proxy sets since proxy user is None or proxy already set")

        os.environ["AWS_SHARED_CREDENTIALS_FILE"] = self.config['aws_credentials']
        os.environ["AWS_CONFIG_FILE"] = self.config['aws_config']

        self.user_data = self.create_user_data()

        self.session = boto3.Session(profile_name=self.config['profile'])

        self.ec2_instances = None

        self.aws_calculator = AWSCostCalculator(self.session)


    def create_user_data(self):
        """creates the user data script depending on experiment type. The user data is built out of base script and specific script depending on experiment type"""

        dir_name = os.path.dirname(os.path.realpath(__file__))

        # If VM is hosted in public the VMs do not need the internal proxy settings
        if self.config['public_ip']:
            with open(f"{dir_name}/UserDataScripts/EC2_instance_bootstrap_base_no_proxy.sh", 'r') as content_file:
                user_data_base = content_file.read()
        else:
            with open(f"{dir_name}/UserDataScripts/EC2_instance_bootstrap_base.sh", 'r') as content_file:
                user_data_base = content_file.read()

        # If blockchain type is base, no specific startup script is needed
        if self.config['blockchain_type'] == 'base':

            user_data_specific = "\n  # =======  Create success indicator at end of this script ==========\n  sudo touch /var/log/user_data_success.log"
            eof = "\nEOF"
            user_data_combined = user_data_base + user_data_specific + eof

        else:
            with open(f"{dir_name}/UserDataScripts/EC2_instance_bootstrap_{self.config['blockchain_type']}.sh", 'r') as content_file:
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

        # If no specific image ID is given search for the newest ubuntu 18 image
        if self.config['image']['image_id'] is None:
            ec2 = self.session.client('ec2', region_name=self.config['aws_region'])

            # Find the latest official Ubuntu image from Canonical(owner = 099720109477)
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


        ec2 = self.session.resource('ec2', region_name=self.config['aws_region'])
        image = ec2.Image(self.config['image']['image_id'])

        self.logger.info("Selected Image: " + image.description)

        session = boto3.Session(profile_name=self.config['profile'])
        ec2 = session.resource('ec2', region_name=self.config['aws_region'])
        self.ec2_instances = ec2.create_instances(
            ImageId=self.config['image']['image_id'],
            MinCount=self.config['vm_count'],
            MaxCount=self.config['vm_count'],
            InstanceType=self.config['instance_type'],
            KeyName=self.config['key_name'],
            #SubnetId=self.config['subnet_id'],
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
            #SecurityGroupIds=self.config['security_group_id'],
             NetworkInterfaces = [
                {
                    'DeviceIndex': 0,
                    'SubnetId': self.config['subnet_id'],
                    'Groups': self.config['security_group_id'],
                    'AssociatePublicIpAddress': self.config['public_ip']
                }]
        )
        self.logger.info(f"Initiated the start of {self.config['vm_count']} {self.config['instance_type']} machines.")
        ips = []
        public_ips = []
        vpc_ids = []
        self.logger.info("Waiting until all VMs are up...")
        for i in self.ec2_instances:
            i.wait_until_running()
            i.load()
            self.logger.info(f"ID: {i.id}, State: {i.state['Name']}, IP: {i.private_ip_address}")
            ips.append(i.private_ip_address)
            vpc_ids.append(i.vpc_id)
            if self.config['public_ip']:
                self.logger.info(f"ID: {i.id}, PUBLIC IP: {i.public_ip_address}")
                public_ips.append(i.public_ip_address)

        # add no proxy for all VM IPs
        if self.config['proxy_user'] is not None:
            os.environ["NO_PROXY"] = f"localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net,{','.join(str(ip) for ip in ips)}"

        self.logger.info(f"You can now access machines via: ssh -i \"path to {self.config['key_name']} key\" ubuntu@{ips} (if user is ubuntu) ")
        self.logger.info(f"e.g. ssh -i {self.config['priv_key_path']} ubuntu@{ips[0]}")

        # add instance IPs and IDs to config
        self.config['ips'] = ips
        self.config['vpc_ids'] = vpc_ids
        if self.config['public_ip']:
            self.config['ips'] = public_ips
            self.config['pub_ips'] = public_ips
            self.config['priv_ips'] = ips
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
        #path = os.getcwd()
        self.config['exp_dir'] = f"{self.config['exp_dir']}/experiments/exp_{st}_{self.config['blockchain_type']}"

        try:

            os.makedirs((f"{self.config['exp_dir']}/user_data_logs"))
            os.makedirs((f"/{self.config['exp_dir']}/setup"))
            self.logger.info(f"Created {str(self.config['exp_dir'])} directory")
        except OSError:
            self.logger.error("Creation of the directories failed")

        with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
            json.dump(self.config, outfile, default=datetimeconverter, indent=4)

        # wait couple minutes until VMs are up
        # first connect ssh clients, then scp client
        self.logger.info("Waiting 60 seconds before creating ssh connection to VMs")
        time.sleep(60)
        ssh_clients, scp_clients = VMHandler.create_ssh_scp_clients(self.config)

        # convert to timedelta for nicer waiting time calcs
        status_flags = np.zeros(self.config['vm_count'], dtype=bool)
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
                        self.logger.info(f"{self.config['ips'][index]} is ready")
                    except IOError:
                        self.logger.info(f"{self.config['ips'][index]} not ready")

        if (False in status_flags):
            self.logger.error('Boot up NOT successful')
            try:
                self.logger.error(f"Failed VMs: {[ips[x] for x in np.where(status_flags != True)]}")
            except:
                pass




            if yes_or_no("Do you want to shut down the VMs?"):

                self.logger.info(f"Running the shutdown script now")
                self.run_general_shutdown()

            else:
                self.logger.info(f"VMs are not being shutdown")

        else:
            self.logger.info(f"Boot up of all VMs was successful, waited {timer} minutes")

            self._run_specific_startup(ssh_clients, scp_clients)



            if 'load_balancer_settings' in self.config and 'add_loadbalancer' in self.config['load_balancer_settings']:
                # Load Balancer
                if self.config['load_balancer_settings']['add_loadbalancer']:
                    self.logger.info("Load Balancer option was chosen, starting the creation routine now")
                    lb_handler = LBHandler(self.config, self.session)
                    lb_handler.creation_routine()

            self.logger.info(
                f"Setup of all {self.config['blockchyin_type}']}-VMs was successful, to terminate them run run.py terminate --config {self.config['exp_dir']}/config.json")
        try:
            map(lambda client: client.close(), ssh_clients)
            map(lambda client: client.close(), scp_clients)
        except:
            self.logger.info("ssh/scp clients already closed")

    def _run_specific_startup(self, ssh_clients, scp_clients):
        """starts startup for given config (geth, parity, etc....)"""

        if self.config['blockchain_type'] == 'fabric':
            fabric_startup(self.ec2_instances, self.config, self.logger, ssh_clients, scp_clients)

        elif self.config['blockchain_type'] == 'geth':
            geth_startup(self.config, self.logger, ssh_clients, scp_clients)

        elif self.config['blockchain_type'] == 'parity':
            try:
                parity_startup(self.config, self.logger, ssh_clients, scp_clients)

            except ParityInstallFailed:
                if yes_or_no("Do you want to shut down the VMs?"):

                    self.logger.info(f"Running the shutdown script now")
                    self.run_general_shutdown()

                else:
                    self.logger.info(f"VMs are not being shutdown")
        if self.config['blockchain_type'] == 'client':
            client_startup(self.config, self.logger, ssh_clients, scp_clients)

        elif self.config['blockchain_type'] == 'quorum':
            quorum_startup(self.config, self.logger, ssh_clients, scp_clients)

        elif self.config['blockchain_type'] == 'sawtooth':
            sawtooth_startup(self.config, self.logger, ssh_clients, scp_clients)

        else:
            pass


    def run_general_shutdown(self):
        """
         Stops and terminates all VMs and calculates causes aws costs.
        :return:
        """
        #TODO: enable stopping and not only termination
        if self.config['proxy_user'] is not None:
            os.environ["NO_PROXY"] = f"localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net,{','.join(str(ip) for ip in self.config['ips'])}"

        ec2 = self.session.resource('ec2', region_name=self.config['aws_region'])
        ec2_instances = ec2.instances.filter(InstanceIds=self.config['instance_ids'])
        if any(instance.state['Name'] == "stopped" for instance in ec2_instances):
            self.logger.info(f"At least on of the instances was already stopped, hence no logs can be pulled from the machines, terminating them in the next step")

        else:
            ssh_clients, scp_clients = VMHandler.create_ssh_scp_clients(self.config)

            for index, ip in enumerate(self.config['ips']):
                # get userData from all instances
                try:
                    scp_clients[index].get("/var/log/user_data.log",
                                           f"{self.config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")
                except:
                    self.logger.info(f"User Data of {ip} cannot be pulled")

            self._run_specific_shutdown(ssh_clients, scp_clients)

            for instance in ec2_instances:
                instance.stop()

        if 'load_balancer_settings' in self.config and 'add_loadbalancer' in self.config['load_balancer_settings']:
            # Load Balancer
            if self.config['load_balancer_settings']['add_loadbalancer']:
                self.logger.info("Starting Load Balancer termination now")
                lb_handler = LBHandler(self.config, self.session)
                lb_handler.shutdown_lb()

        # calculate aws costs
        self.aws_calculator.calculate_uptime_costs(self.config)

        for instance in ec2_instances:
            instance.terminate()


        self.logger.info("All instances terminated -  script is finished")

    def _run_specific_shutdown(self, ssh_clients, scp_clients):
        """Runs the specific shutdown scripts depending on blockchain_type"""

        if self.config['blockchain_type'] == 'geth':
            geth_shutdown(self.config, self.logger, ssh_clients, scp_clients)

        elif self.config['blockchain_type'] == 'parity':
            parity_shutdown(self.config, self.logger, ssh_clients, scp_clients)

        else:
            pass

    def get_config_path(self):
        return f"{self.config['exp_dir']}/config.json"

    def get_config(self):
        return self.config

    def set_target_network_conf(self, dir_name):
        """
        Needed by ChainLab project to set network_config after parallelism is finished
        :param dir_name: Name of target_network_conf
        :return:
        """
        self.config['client_settings']['target_network_conf'] = dir_name

        with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
            json.dump(self.config, outfile, default=datetimeconverter, indent=4)

    @staticmethod
    def create_ssh_scp_clients(config):
        """
        Creates ssh/scp connection to aws VMs

        :param config:
        :return: array of scp and ssh clients
        """
        ssh_clients = []
        scp_clients = []
        ssh_key_priv = paramiko.RSAKey.from_private_key_file(config['priv_key_path'])

        for index, ip in enumerate(config['ips']):
            if config['public_ip']:
                #use public ip if exists, else it wont work
                ip = config['pub_ips'][index]
            ssh_clients.append(paramiko.SSHClient())
            ssh_clients[index].set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_clients[index].connect(hostname=ip, username=config['user'], pkey=ssh_key_priv)
            # ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(cmd_to_execute)

            # SCPCLient takes a paramiko transport as an argument
            scp_clients.append(SCPClient(ssh_clients[index].get_transport()))

        return ssh_clients, scp_clients




def datetimeconverter(o):
    """Converter to make datetime objects json dumpable"""
    if isinstance(o, datetime.datetime):
        return o.__str__()

def yes_or_no(question):
    reply = str(input(question + ' (y/n): ')).lower().strip()
    if reply[0] == 'y':
        return 1
    elif reply[0] == 'n':
        return 0
    else:
        return yes_or_no("Please Enter (y/n) ")
