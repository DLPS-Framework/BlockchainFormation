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


import getpass
import os
import paramiko
import sys

import boto3
import pytz
from dateutil import parser
from scp import SCPClient

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from BlockchainFormation.cost_calculator import AWSCostCalculator

from BlockchainFormation.blockchain_specifics.acapy.Acapy_Network import *
from BlockchainFormation.blockchain_specifics.besu.Besu_Network import *
from BlockchainFormation.blockchain_specifics.client.Client_Network import *
from BlockchainFormation.blockchain_specifics.corda.Corda_Network import *
from BlockchainFormation.blockchain_specifics.couchdb.Couchdb_Network import *
from BlockchainFormation.blockchain_specifics.fabric.Fabric_Network import *
from BlockchainFormation.blockchain_specifics.empty.Empty_Network import *
from BlockchainFormation.blockchain_specifics.eos.Eos_Network import *
from BlockchainFormation.blockchain_specifics.ethermint.Ethermint_Network import *
from BlockchainFormation.blockchain_specifics.geth.Geth_Network import *
from BlockchainFormation.blockchain_specifics.indy.Indy_Network import *
from BlockchainFormation.blockchain_specifics.indy_client.Indy_client_Network import *
from BlockchainFormation.blockchain_specifics.leveldb.Leveldb_Network import *
from BlockchainFormation.blockchain_specifics.parity.Parity_Network import *
from BlockchainFormation.blockchain_specifics.quorum.Quorum_Network import *
from BlockchainFormation.blockchain_specifics.sawtooth.Sawtooth_Network import *
from BlockchainFormation.blockchain_specifics.tendermint.Tendermint_Network import *
from BlockchainFormation.blockchain_specifics.tezos.Tezos_Network import *
from BlockchainFormation.blockchain_specifics.vendia.Vendia_Network import *

from BlockchainFormation.utils import utils

utc = pytz.utc


class Node_Handler:
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
        self.user_data = self.create_user_data()

        try:

            if self.config['instance_provision'] == 'aws':
                self.logger.info("Automatic startup in AWS selected")
            elif self.config['instance_provision'] == 'own':
                self.logger.info("Automatic startup on user-proxided instances selected")
            else:
                self.logger.info("Invalid option")
                raise Exception("No valid option for cloud specified")

        except Exception as e:
            self.logger.info("AWS config by default")
            self.config['instance_provision'] = 'aws'

        if self.config['instance_provision'] == 'aws':
            # no proxy if no proxy user
            if self.config['proxy'] is not None and "HTTP_PROXY" not in os.environ:

                if self.config['proxy']['proxy_user'] is not None:
                    password = getpass.getpass(prompt=f"Enter proxy password for {self.config['proxy']['proxy_user']}:")
                    os.environ["HTTPS_PROXY"] = f"http://{self.config['proxy']['proxy_user']}:{password}@{self.config['proxy']['http_proxy']}"
                    os.environ["HTTP_PROXY"] = f"http://{self.config['proxy']['proxy_user']}:{password}@{self.config['proxy']['https_proxy']}"
                else:
                    os.environ["HTTPS_PROXY"] = f"http://{self.config['proxy']['https_proxy']}"
                    os.environ["HTTP_PROXY"] = f"http://{self.config['proxy']['http_proxy']}"

                os.environ["NO_PROXY"] = self.config['proxy']['no_proxy']

            else:
                self.logger.info("No proxy set since proxy user is None or proxy already set")

            # This is needed that boto3 knows where to find the aws config and credentials
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = self.config['aws_credentials']
            os.environ["AWS_CONFIG_FILE"] = self.config['aws_config']

            self.session = boto3.Session(profile_name=self.config['profile'])
            self.ec2_instances = None
            self.aws_calculator = AWSCostCalculator(self.session)

    def create_user_data(self):
        """creates the user data script depending on experiment type. The user data is built out of base script and
        specific script depending on experiment type"""

        dir_name = os.path.dirname(os.path.realpath(__file__))

        user_data_base = ""

        try:

            if self.config['instance_provision'] == "aws":

                with open(f"{dir_name}/UserDataScripts/bootstrap_base_aws.sh", 'r') as content_file:
                    user_data_base = content_file.read()

            elif self.config['instance_provision'] == "own":

                with open(f"{dir_name}/UserDataScripts/bootstrap_base_own.sh", 'r') as content_file:
                    user_data_base = content_file.read()

        except Exception as e:

            with open(f"{dir_name}/UserDataScripts/bootstrap_base_aws.sh", 'r') as content_file:
                user_data_base = content_file.read()

                self.config['instance_provision'] = 'aws'

        # If VM is hosted in public the VMs do not need the internal proxy settings
        if (self.config['instance_provision'] == 'aws') and (not self.config['public_ip']):
            # Is this the best solution to set proxy dynamically?
            proxy_user_data = f"  HTTP_PROXY={self.config['aws_proxy_settings']['aws_http_proxy']}\n" \
                              f"  HTTPS_PROXY={self.config['aws_proxy_settings']['aws_https_proxy']}\n" \
                              f"  NO_PROXY={self.config['aws_proxy_settings']['aws_no_proxy']}\n" \
                              f"  export http_proxy=$HTTP_PROXY\n" \
                              f"  export https_proxy=$HTTPS_PROXY\n" \
                              f"  export no_proxy=$NO_PROXY\n" \
                              f"  bash -c \"sudo echo http_proxy=$HTTP_PROXY >> /etc/environment\"\n" \
                              f"  bash -c \"sudo echo https_proxy=$HTTPS_PROXY >> /etc/environment\"\n" \
                              f"  bash -c \"sudo echo no_proxy=$NO_PROXY >> /etc/environment\"\n" \
                              f"  sudo touch /etc/profile.d/environment_mods.sh\n" \
                              f"  bash -c \"sudo echo http_proxy=$HTTP_PROXY >> /etc/profile.d/environment_mods.sh\"\n" \
                              f"  bash -c \"sudo echo https_proxy=$HTTPS_PROXY >> /etc/profile.d/environment_mods.sh\"\n" \
                              f"  bash -c \"sudo echo no_proxy=$NO_PROXY >> /etc/profile.d/environment_mods.sh\"\n"

            user_data_base = user_data_base.replace("  # PROXY_PLACEHOLDER, DO NOT DELETE!", proxy_user_data)

        # If blockchain type is base, no specific startup script is needed
        if self.config['blockchain_type'] == 'base':

            user_data_specific = "\n  # =======  Create success indicator at end of this script ==========\n  sudo touch /var/log/user_data_success.log"
            eof = "\nEOF"
            user_data_combined = user_data_base + user_data_specific + eof

        # if the blockchain type is fabric, we can modify the version of the docker images
        elif self.config['blockchain_type'] == 'fabric':

            os.system(f"cp {dir_name}/blockchain_specifics/fabric/bootstrap_fabric.sh {dir_name}/blockchain_specifics/fabric/bootstrap_fabric_temp.sh")
            os.system(f"sed -i -e 's/substitute_fabric_version/{self.config['fabric_settings']['fabric_version']}/g' {dir_name}/blockchain_specifics/fabric/bootstrap_fabric_temp.sh")
            os.system(f"sed -i -e 's/substitute_fabric_ca_version/{self.config['fabric_settings']['fabric_ca_version']}/g' {dir_name}/blockchain_specifics/fabric/bootstrap_fabric_temp.sh")
            os.system(f"sed -i -e 's/substitute_fabric_thirdparty_version/{self.config['fabric_settings']['thirdparty_version']}/g' {dir_name}/blockchain_specifics/fabric/bootstrap_fabric_temp.sh")

            with open(f"{dir_name}/blockchain_specifics/fabric/bootstrap_fabric_temp.sh", 'r') as content_file:
                user_data_specific = content_file.read()

            user_data_combined = user_data_base + user_data_specific

            os.system(f"rm {dir_name}/blockchain_specifics/fabric/bootstrap_fabric_temp.sh")

        elif self.config['blockchain_type'] == 'eos':

            # if we have non-standard settings, we need to compile binaries from scratch
            if Eos_Network.check_config(self.config, self.logger):
                replace_command = "sudo apt-get install -y make " \
                                  "&& mkdir -p /data/eosio && cd /data/eosio " \
                                  "&& git clone --recursive https://github.com/EOSIO/eos && cd eos " \
                                  "&& git pull --recurse-submodules && git submodule update --init --recursive " \
                                  "&& cd /data/eosio/eos && yes | ./scripts/eosio_build.sh " \
                                  "&& cd /data/eosio/eos/build && sudo make install && sudo mv bin/* /usr/local/bin " \
                                  f"&& sed -i -e 's/block_interval_ms = 500/block_interval_ms = {self.config['eos_settings']['block_interval_ms']}/g' /data/eosio/eos/libraries/chain/include/eosio/chain/config.hpp"
            else:
                replace_command = "wget https://github.com/EOSIO/eos/releases/download/v2.0.3/eosio_2.0.3-1-ubuntu-18.04_amd64.deb && sudo apt install -y ./eosio_2.0.3-1-ubuntu-18.04_amd64.deb"

            os.system(f"cp {dir_name}/blockchain_specifics/eos/bootstrap_eos.sh {dir_name}/blockchain_specifics/eos/bootstrap_eos_temp.sh")
            os.system(f"sed -i -e \"s#substitute_replace_command#{replace_command}#g\" {dir_name}/blockchain_specifics/eos/bootstrap_eos_temp.sh")
            os.system(f"sed -i -e 's/substitute_replace_commandsubstitute_replace_command/\&\&/g' {dir_name}/blockchain_specifics/eos/bootstrap_eos_temp.sh")

            with open(f"{dir_name}/blockchain_specifics/eos/bootstrap_eos_temp.sh", 'r') as content_file:
                user_data_specific = content_file.read()

            user_data_combined = user_data_base + user_data_specific

            os.system(f"rm {dir_name}/blockchain_specifics/eos/bootstrap_eos_temp.sh")

        else:

            with open(f"{dir_name}/blockchain_specifics/{self.config['blockchain_type']}/bootstrap_{self.config['blockchain_type']}.sh", 'r') as content_file:
                user_data_specific = content_file.read()

            user_data_combined = user_data_base + user_data_specific

        return user_data_combined

    def run_general_startup(self):
        """
        General startup script needed for all blockchain frameworks. After general part is finished, the specific startup script are kicked off
        :return:
        """

        try:
            if self.config['instance_provision'] == "aws":
                self.logger.info("Launching the required instances in aws")

            elif self.config['instance_provision'] == "own":
                self.logger.info(f"Using existing instances on ips {self.config['ips']}")
                self.logger.info(f"Note that the user currently needs to run Ubuntu 18.04, the user name for ssh'ing must be 'ubuntu'"
                                 f", and the instances require a directory /data/ with permissions set for ubuntu and at least 8 GB of storage")

        except Exception as e:
            self.logger.info("AWS by default")

        self.logger.info("Checking consistency of the region")
        if type(self.config["aws_region"]) is dict:
            count = 0
            for key in self.config["aws_region"]:
                count = count + self.config["aws_region"][key]

            self.logger.info(f"Different regions; in total there are {count} instances")
            if count != self.config["vm_count"]:
                self.logger.info("Inconsistent")
                raise Exception("Error: Inconsistent number of nodes in the regions")
            else:
                self.logger.info("All right")

        else:
            region = self.config["aws_region"]
            self.config["aws_region"] = {}
            self.config["aws_region"][region] = self.config["vm_count"]


        if type(self.config["subnet_id"]) is dict:
            pass
        else:
            subnet_id = self.config["subnet_id"]
            self.config["subnet_id"] = {}
            self.config["subnet_id"][region] = subnet_id

        if type(self.config["security_group_id"]) is dict:
            pass
        else:
            security_group_id = self.config["security_group_id"]
            self.config["security_group_id"] = {}
            self.config["security_group_id"][region] = security_group_id

        self.logger.info(f"New region: {self.config['aws_region']}")

        if self.config['blockchain_type'] == "fabric":
            Fabric_Network.check_config(self.config, self.logger)

        elif self.config['blockchain_type'] == 'corda':
            Corda_Network.check_config(self.config, self.logger)

        elif self.config['blockchain_type'] == "eos":
            # check_config is currently executed below
            # eos_check_config(self.config, self.logger)
            pass

        elif self.config['blockchain_type'] == "sawtooth":
            Sawtooth_Network.check_config(self.config, self.logger)
            
        self.get_image_ids()

        if self.config['instance_provision'] == "aws" and self.config["vm_count"] > 0:

            self.start_instances()
            
            self.logger.info(f"Initiated the start of {self.config['vm_count']} {self.config['instance_type']} machines.")
            ips = [0] * self.config['vm_count']
            public_ips = [0] * self.config['vm_count']
            vpc_ids = [0] * self.config['vm_count']
            self.logger.info("Waiting until all VMs are up...")
            self.logger.info(f"{self.ec2_instances}")
            for index1, region in enumerate(self.config["aws_region"]):
                for index2, i in enumerate(self.ec2_instances[region]):
                    pos = index1 + index2 * len(self.config["aws_region"].keys())
                    self.logger.info(pos)
                    i.wait_until_running()
                    i.load()
                    ips[pos] = i.private_ip_address
                    vpc_ids[pos] = i.vpc_id
                    if self.config['public_ip']:
                        public_ips[pos] = i.public_ip_address

            self.logger.info(f"IPs: {ips}")


            # add no proxy for all VM IPs
            if self.config['proxy'] is not None:
                # Careful that you do NOT delete old NO_PROXY settings, hence the os.environ["NO_PROXY"] + new
                os.environ["NO_PROXY"] = os.environ["NO_PROXY"] + f",{','.join(str(ip) for ip in ips)}"

            # add instance IPs and IDs to config
            self.config['ips'] = ips
            self.config['vpc_ids'] = vpc_ids
            if len(self.config['aws_region'].keys()) == 1:
                self.config['priv_ips'] = ips
            else:
                self.config['priv_ips'] = public_ips
            if self.config['public_ip']:
                self.config['ips'] = public_ips
                self.config['pub_ips'] = public_ips
            else:
                self.config['pub_ips'] = ips

            self.config["instance_ids"] = {}
            for region in self.config["aws_region"]:
                self.config['instance_ids'][region] = [instance.id for instance in self.ec2_instances[region]]

            self.logger.info(f"You can now access machines via: ssh -i \"path to {self.config['key_name']} key\" ubuntu@{self.config['ips']} (if user is ubuntu) ")
            self.logger.info(f"e.g. ssh -i {self.config['priv_key_path']} ubuntu@{self.config['ips'][0]}")

            # Give launched instances tag with time/type of experiment/number of node
            ts = time.time()
            st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
            for region in self.config["aws_region"]:
                ec2 = self.session.resource('ec2', region_name=region)
                for index, i in enumerate(self.ec2_instances[region]):
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

            self.launch_times = {}
            for region in self.config["aws_region"]:
                self.launch_times[region] = []
                for i in self.ec2_instances[region]:
                    # self.logger.info("Launch Time: " + str(i.launch_time))
                    # get launch time
                    self.launch_times[region].append(i.launch_time.replace(tzinfo=None))

            # create experiment directory structure
            self.config['launch_times'] = self.launch_times

        elif (self.config['instance_provision'] == "own" and self.config['vm_count'] > 0):

            self.config['vm_count'] = len(self.config['pub_ips'])
            if self.config['vm_count'] == len(self.config['pub_ips']) and self.config['vm_count'] == len(self.config['priv_ips']) and self.config['vm_count'] == len(self.config['ips']):

                # writing the user data to a file
                with open(f"{self.config['exp_dir']}/bootstrapping.sh", "w") as file:
                    file.write(self.user_data)
                    file.close()

                self.create_ssh_scp_clients()

                for index in range(0, self.config['vm_count']):
                    # deleting previous indicators of success
                    stdin, stdout, stderr = self.ssh_clients[index].exec_command("sudo rm -rf /var/log/user_data.log /var/log/user_data_success.log")
                    wait_and_log(stdout, stderr)

                    self.scp_clients[index].put(self.config['exp_dir'] + "/bootstrapping.sh", "/home/ubuntu")

                    stdin, stdout, stderr = self.ssh_clients[index].exec_command("sudo chmod 775 /home/ubuntu/bootstrapping.sh")
                    wait_and_log(stdout, stderr)

                    channel = self.ssh_clients[index].get_transport().open_session()
                    channel.exec_command("sudo /home/ubuntu/bootstrapping.sh")

            else:
                raise Exception("Inconsistent lengths of the ip fields compared to vm_count")

        elif self.config["vm_count"] == 0:
            self.config["ips"] = []
            self.config["pub_ips"] = []
            self.config["priv_ips"] = []

        else:
            self.logger.info("Neither AWS nor own IPs nor 0 nodes deployed")
            raise Exception("Invalid configuration")

        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d_%H-%M-%S')
        self.config['exp_dir'] = f"{self.config['exp_dir']}/experiments/exp_{st}_{self.config['blockchain_type']}"

        try:

            os.makedirs(f"{self.config['exp_dir']}/user_data_logs")
            os.makedirs(f"/{self.config['exp_dir']}/setup")
            self.logger.info(f"Created {str(self.config['exp_dir'])} directory")
        except OSError:
            self.logger.error("Creation of the directories failed")

        with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
            json.dump(self.config, outfile, default=datetimeconverter, indent=4)

        if self.config['instance_provision'] is not "none":
            # wait couple minutes until VMs are up
            # first connect ssh clients, then scp client
            if self.config['vm_count'] > 0:
                self.logger.info("Waiting 60 seconds before creating ssh connection to VMs")
                time.sleep(60)
            self.create_ssh_scp_clients()

        self.logger.info("Waiting for all VMs to finish the userData setup...")

        if self.config['blockchain_type'] == "eos":
            max_time = 120
            normal_time = 60
        elif self.config['blockchain_type'] == "tezos":
            max_time = 60
            normal_time = 30
        else:
            max_time = 30
            normal_time = 10

        # Wait until user Data is finished
        if False in wait_till_done(self.config, self.ssh_clients, self.config['ips'], max_time * 60, 60,
                                   "/var/log/user_data_success.log", False, normal_time * 60, self.logger):
            self.logger.error('Boot up NOT successful')

            if yes_or_no("Do you want to shut down the VMs?"):

                self.logger.info(f"Running the shutdown script now")
                self.run_general_shutdown()

            else:
                self.logger.info(f"VMs are not being shutdown")

        else:
            self.logger.info(f"Boot up of all {self.config['blockchain_type']}-VMs was successful")

            self.refresh_ssh_scp_clients()

            self._run_specific_startup()

            if 'load_balancer_settings' in self.config and 'add_loadbalancer' in self.config['load_balancer_settings']:
                # Load Balancer
                if self.config['load_balancer_settings']['add_loadbalancer']:
                    self.logger.info("Load Balancer option was chosen, starting the creation routine now")
                    lb_handler = LBHandler(self.config, self.session, region)
                    lb_handler.creation_routine()

            self.logger.info(
                f"Setup of all VMs was successful, to terminate them run run.py terminate --config {self.config['exp_dir']}/config.json")

        self.close_ssh_scp_clients()

        # if yes_or_no("Do you want to shut down the whole network?"):
        # self.run_general_shutdown()

    def _run_specific_startup(self):
        """starts startup for given config (geth, parity, etc....)"""

        # running the blockchain specific startup script
        self.startup_network()

        with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
            json.dump(self.config, outfile, default=datetimeconverter, indent=4)

        # close ssh and scp channels
        self.close_ssh_scp_clients()

    def run_general_shutdown(self):
        """
         Stops and terminates all VMs and calculates causes aws costs.
        :return:
        """

        # create ssh and scp channels
        self.create_ssh_scp_clients()

        for index, ip in enumerate(self.config['ips']):
            # get userData from all instances
            try:
                self.scp_clients[index].get("/var/log/user_data.log",
                                       f"{self.config['exp_dir']}/user_data_logs/user_data_log_node_{index}.log")
            except:
                self.logger.info(f"User Data of {ip} cannot be pulled")

        if self.config['instance_provision'] == "aws":

            self.logger.info("Shutting down the instances in AWS")

            if self.config['proxy'] is not None:
                os.environ["NO_PROXY"] = f"{self.config['proxy']['no_proxy']},{','.join(str(ip) for ip in self.config['ips'])}"

            self.ec2_instances = {}
            for region in self.config["aws_region"]:
                ec2 = self.session.resource('ec2', region_name=region)
                try:
                    self.ec2_instances[region] = ec2.instances.filter(InstanceIds=self.config['instance_ids'][region])
                    self.logger.info(f"There are {sum(1 for _ in self.ec2_instances[region])} instances in region {region}")
                except Exception as e:
                    self.logger.exception(e)
                    self.ec2_instances[region] = []

                if any(instance.state['Name'] == "stopped" for instance in self.ec2_instances[region]):
                    self.logger.info(f"At least on of the instances was already stopped, hence no logs can be pulled from the machines, terminating them in the next step")

                    self._run_specific_shutdown()

        if self.config['instance_provision'] == "aws":

            for region in self.config["aws_region"]:
                for instance in self.ec2_instances[region]:
                    instance.stop()

                if 'load_balancer_settings' in self.config and 'add_loadbalancer' in self.config['load_balancer_settings']:
                    # Load Balancer
                    if self.config['load_balancer_settings']['add_loadbalancer']:
                        self.logger.info("Starting Load Balancer termination now")
                        lb_handler = LBHandler(self.config, self.session, region)
                        lb_handler.shutdown_lb()

            # calculate aws costs
            self.aws_calculator.calculate_uptime_costs(self.config)

            for region in self.config["aws_region"]:
                for instance in self.ec2_instances[region]:
                    instance.terminate()

        # close ssh and scp channels
        self.close_ssh_scp_clients()
        self.logger.info("All instances terminated -  script is finished")

    def _run_specific_shutdown(self):
        """Runs the specific shutdown scripts depending on blockchain_type"""

        # running the blockchain specific startup script
        self.shutdown_network()

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
        print(f"Dir_name in set_target_network_conf: " + dir_name)

        with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
            json.dump(self.config, outfile, default=datetimeconverter, indent=4)


    def create_ssh_scp_clients(self):
        """
        Creates ssh/scp connection to VMs
        :param config:
        :param logger:
        :return: array of scp and ssh clients
        """
        ssh_clients = []
        scp_clients = []
        ssh_key_priv = paramiko.RSAKey.from_private_key_file(self.config['priv_key_path'])

        if self.logger is not None:
            # logger.debug(f"Trying to connect the ssh clients")
            pass

        self.logger.info(self.config['ips'])
        for index, ip in enumerate(self.config['ips']):
            if self.config['public_ip']:
                # use public ip if exists, else it wont work
                ip = self.config['pub_ips'][index]
            ssh_clients.append(paramiko.SSHClient())
            ssh_clients[index].set_missing_host_key_policy(paramiko.AutoAddPolicy())

            while True:
                try:
                    ssh_clients[index].connect(hostname=ip, username=self.config['user'], pkey=ssh_key_priv, timeout=86400, banner_timeout=100, auth_timeout=30)

                except Exception as e:
                    if self.logger is not None:
                        self.logger.error(f"{e} on IP {ip}")
                    else:
                        print(f"{e} on IP {ip}")
                    try:
                        ssh_clients[index].close()
                        ssh_clients[index] = paramiko.SSHClient()
                        ssh_clients[index].set_missing_host_key_policy(paramiko.AutoAddPolicy())

                    except Exception as e:
                        if self.logger is not None:
                            self.logger.error(f"{e} on IP {ip}")
                        else:
                            print(f"{e} on IP {ip}")

                else:
                    break

            # SCPCLient takes a paramiko transport as an argument
            scp_clients.append(SCPClient(ssh_clients[index].get_transport(), socket_timeout=86400, progress=Node_Handler.progress))

        if self.logger is not None:
            # logger.debug(f"All scp/ssh clients got created and connected")
            pass

        self.ssh_clients = ssh_clients
        self.scp_clients = scp_clients

    def refresh_ssh_scp_clients(self):

        # Recreating the ssh and scp clients
        self.close_ssh_scp_clients()
        self.create_ssh_scp_clients()

    def close_ssh_scp_clients(self):

        try:
            map(lambda client: client.close(), self.ssh_clients)
            map(lambda client: client.close(), self.scp_clients)
        except:
            self.logger.info("ssh/scp clients already closed")

    def shutdown_network(self):

        blockchain_type = self.config['blockchain_type']

        try:
            func = getattr(globals()[f"{blockchain_type.capitalize()}_Network"], "shutdown")
            func(self)

        except Exception as e:

            self.logger.exception(e)
            raise Exception("")


    def restart_network(self):

        blockchain_type = self.config['blockchain_type']

        try:
            func = getattr(globals()[f"{blockchain_type.capitalize()}_Network"], "restart")
            func(self)

        except Exception as e:

            self.logger.exception(e)
            raise Exception("")


    def startup_network(self):

        blockchain_type = self.config['blockchain_type']

        if blockchain_type in ["ethermint", "qldb", "tezos"]:
            self.logger.warning("")
            self.logger.warning("")
            self.logger.warning(f"  !!! The automatic setup for {blockchain_type.upper()} is not yet working - still under active development  !!!")
            self.logger.warning("")
            self.logger.warning("")

        try:
            func = getattr(globals()[f"{blockchain_type.capitalize()}_Network"], "startup")
            func(self)

        except Exception as e:
            self.logger.exception(e)
            raise Exception("Network startup failed")


    def restart_network(self):

        blockchain_type = self.config['blockchain_type']

        try:
            func = getattr(globals()[f"{blockchain_type.capitalize()}_Network"], "restart")
            func(self)

        except Exception as e:

            self.logger.exception(e)
            raise Exception("")

    @staticmethod
    def progress(filename, size, sent):
        sys.stdout.write("%s\'s progress: %.2f%%   \r" % (filename, float(sent) / float(size) * 100))

    def get_image_ids(self):
        
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

        if (self.config['instance_provision'] == 'aws' and self.config['vm_count'] > 0):

            self.config['image']['image_ids'] = {}
            for region in self.config["aws_region"]:

                # If no specific image ID is given search for the newest ubuntu 18 image
                if self.config['image']['image_id'] is None:
                    ec2 = self.session.client('ec2', region_name=region)

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
                    self.config['image']['image_ids'][region] = image["ImageId"]

            self.logger.info(f"Image IDs: {self.config['image']['image_ids']}")
            
    def start_instances(self):

        self.ec2_instances = {}

        for region in self.config["aws_region"]:

            ec2 = self.session.resource('ec2', region_name=region)
            image = ec2.Image(self.config['image']['image_ids'][region])

            self.logger.info(f"Selected Image for region {region}: " + image.description)

            session = boto3.Session(profile_name=self.config['profile'])
            ec2 = session.resource('ec2', region_name=region)
            self.ec2_instances[region] = ec2.create_instances(
                ImageId=self.config['image']['image_ids'][region],
                MinCount=self.config['aws_region'][region],
                MaxCount=self.config['aws_region'][region],
                InstanceType=self.config['instance_type'],
                KeyName=self.config['key_name'],
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
                InstanceMarketOptions={
                    'MarketType': 'spot',
                    'SpotOptions': {
                        # 'MaxPrice': 'string',
                        'SpotInstanceType': 'one-time',  # | 'persistent'
                        'BlockDurationMinutes': 240,
                        'InstanceInterruptionBehavior': 'terminate'
                    }

                } if 'aws_spot_instances' in self.config and self.config['aws_spot_instances'] else {},
                NetworkInterfaces=[
                    {
                        'DeviceIndex': 0,
                        'SubnetId': self.config['subnet_id'][region],
                        'Groups': self.config['security_group_id'][region],
                        'AssociatePublicIpAddress': self.config['public_ip']
                    }]
            )