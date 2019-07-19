# EC2 Automation Script

## Major Updates:
 * *July 1 2019:* Added Application LoadBalancer Support (so far only for private VPCs)
 * *June 17 2019:* Added Parity Support

## General Information

The purpose of this script is to automate the process of deploying blockchain solutions on aws.
This process includes starting ```x``` ec2 instances, installing necessary packages and configure the virtual machines.
The provided VMs then can used for example to evaluate the performance of a given blockchain solution.
If the network is not needed anymore, the script provides  a function to shutdown all started VMs after pulling log files.
The shutdown script also calculates the aws costs caused by the uptime of the virtual machines using the aws pricing API.

 *NOTE THAT THE CREATED BLOCKCHAIN NODES ARE NOT CONFIGURED WITH HIGH SECURITY SETTINGS* 
## How to run it

```run.py``` provides a argpass CLI for starting and terminating VMs. 

* Start a private Geth Network with PoA consensus: 


```
python run.py start geth --vm_count 4 --instance_type t2.micro --priv_key_path ~/.ssh/blockchain --tag_name blockchain_philipp 
--subnet_id subnet-0ac7aeeec87150dd7 --security_group_id sg-0db312b6f84d66889 --aws_credentials ~/.aws/credentials --aws_config ~/.aws/config 
--profile block_exp --key_name blockchain  --VolumeSize 32 --proxy_user qqdpoc0 --chainid 11
```
__This is an example for a run command, values need to be adjusted for your config__

* Start a Base Network where __NO__ blockchain frameworks will be installed, just x VMs with the base installations (e.g. proxy)


```
python run.py start base --vm_count 4 --instance_type t2.micro --priv_key_path ~/.ssh/blockchain --tag_name blockchain_philipp 
--subnet_id subnet-0ac7aeeec87150dd7 --security_group_id sg-0db312b6f84d66889 --aws_credentials ~/.aws/credentials --aws_config ~/.aws/config 
--profile block_exp --key_name blockchain  --VolumeSize 32 --proxy_user qqdpoc0
```
__This is an example for a run command, values need to be adjusted for your config__


Explanation of common flags (needed for all blockchains, not only e.g. geth):
```
  --vm_count VM_COUNT, -vmc VM_COUNT
                        specify how many VM you want to start
  --instance_type {t2.nano,t2.micro,t2.small,t2.medium,t2.large,t2.xlarge,t2.2xlarge}, -it {t2.nano,t2.micro,t2.small,t2.medium,t2.large,t2.xlarge,t2.2xlarge}
                        specify what type of instances you want to start [default=t2.micro]
  --aws_credentials AWS_CREDENTIALS, -cred AWS_CREDENTIALS
                        path to aws credentials [default=~.aws/credentials]
  --key_name KEY_NAME, -kn KEY_NAME
                        name of aws credentials key [default=blockchain]
  --aws_config AWS_CONFIG, -aws_con AWS_CONFIG
                        path to aws config [default=~.aws/config]
                        
  --aws_region AWS_REGION, -aws_r AWS_REGION
                        aws region where images should be hosted [default=eu-central-1]                   
  --priv_key_path PRIV_KEY_PATH, -key PRIV_KEY_PATH
                        path to ssh key [default=~.ssh/blockchain]
  --image_id IMAGE_ID, -img_id IMAGE_ID
                        image ID for vm, note that images other than ubuntu are not supported by startup script [default=None (the script then pulls newest ubuntu 18 img)]
  --image_version IMAGE_VERSION, -img_v IMAGE_VERSION
                        ubuntu version (default = 18)                                               
  --VolumeSize VOLUMESIZE, -s VOLUMESIZE
                        amount of extra storage in GB: min 8, max 1024 [default=32]
  --KmsKeyId KMSKEYID, -KId KMSKEYID
                        KmsKeyId for Encryption, None for no Encryption [default=arn:aws:kms:eu-central-1:731899578576:key/a808826d-e460-4271-a23b-29e1e0807c1d]                       
  --profile PROFILE, -p PROFILE
                        name of aws profile [default=block_exp]
  --tag_name TAG_NAME, -t TAG_NAME     tag for aws [default=blockchain_experiment]
  --exp_dir EXP_DIR, -exp_d EXP_DIR
                        Directory where experiment folder is created
                        (default=os.getcwd())
  --subnet_id SUBNET_ID, -st SUBNET_ID
                        subnet id [default=subnet-0ac7aeeec87150dd7]
  --security_group_id SECURITY_GROUP_ID [SECURITY_GROUP_ID ...], -sg SECURITY_GROUP_ID [SECURITY_GROUP_ID ...]
                        security group, multiple values allowed [default=sg-0db312b6f84d66889]
  --public_ip PUBLIC_IP, -pub_ip PUBLIC_IP
                        True or False if public IP is needed (remember to
                        define correct subnet/security)) [default=False]                   
  --proxy_user PROXY_USER, -pu PROXY_USER
                        enter q number for proxy; None for no proxy [default=qqdpoc0]
```
Explanation of Load Balancer flags:
```
  --add_loadbalancer ADD_LOADBALANCER, -add_lb ADD_LOADBALANCER
                        True or False whether you want a application load
                        balancer [default=False]  
  --lb_subnet_ids LB_SUBNET_IDS, -_lb_st LB_SUBNET_IDS
                        load balancer subnet ids (at least two from different
                        availability zones) [default=['subnet-0ac7aeeec87150dd7','subnet-0af1a4489042c2d42']]  
  --lb_security_group_ids LB_SECURITY_GROUP_IDS [LB_SECURITY_GROUP_IDS ...], -lb_sg LB_SECURITY_GROUP_IDS [LB_SECURITY_GROUP_IDS ...]
                        security group, multiple values allowed [default=["sg-0db312b6f84d66889"]]  
  --lb_port LB_PORT, -lb_p LB_PORT
                        which port should load balancer listen AND hit [default=8545]  
  --lb_hosted_zone_id HOSTED_ZONE_ID, -hzi HOSTED_ZONE_ID
                        hosted zone id for route 53 [default=Z1M5DW26LY28R0] 

```

Explanation of specific geth flags:
```
  --chainid CHAINID, -ci CHAINID
                        specify chainID [default=11]
  --period PERIOD, -pd PERIOD
                        specify clique period [default=5]
  --epoch EPOCH, -eh EPOCH
                        specify clique epoch [default=30000]
  --balance BALANCE, -bal BALANCE
                        specify start balance of account [default=0x200000000000000000000000000000000000000000000000000000000000000]
  --timestamp TIMESTAMP, -tp TIMESTAMP
                        specify timestamp of genesis [default=0x00]
  --gaslimit GASLIMIT, -gl GASLIMIT
                        specify gasLimit [default=0x2fefd8]
  --num_acc NUM_ACC, -na NUM_ACC
                        specify number of accounts added to each node [default=None -> every node gets a unique account]                        

```

Explanation of specific parity flags:
```
  --step_duration STEP_DURATION, -sd STEP_DURATION
                        specify step_duration  [default=5]
  --num_acc NUM_ACC, -na NUM_ACC
                        specify number of accounts added to each node [default=None -> every node gets a unique account]      
  --gaslimit GASLIMIT, -gl GASLIMIT
                        specify gasLimit [default=0x5B8D80]
  --balance BALANCE, -bal BALANCE
                        specify start balance of account [default=0x200000000000000000000000000000000000000000000000000000000000000]

```

__Note that you need to enter the password for your proxy user after starting the script__


*If you do not want to create the large CLI every time you can also  start a network with a given config file:*
```
python run.py start --config "path to config file" 
```
Example config files for geth, parity and base are provided in ```/example_config_files/base_config.json```

*WARNING:* Config files and CLI arguments cannot be combined at the moment, so either use the config file to pass arguments or pass all arguments via argpass commands.

* Terminate a VM Network:

```
python run.py terminate --config "path to config file" 
```

## How to add another blockchain?
To add another blockchain 4 things need to be added:
* Write specific startup/shutdown in e.g. ```/blockchain_specifics/Geth.py```
* add specific startup function in ```vm_handler.py```
* add specific shutdown function in ```vm_handler.py```
* adjustments of argpass CLI and config in ```run.py```
* specific user data script in ```/UserDataScripts```

## Future Steps
* Add InstanceMarketOptions for cheapter VMs (Does the AWS Calculator take care of this?)
* Add Windows support
* Add option to attach no storage at all
* Make geth/parity setup even more customizable
* Add logrotate to UserData setup scripts
*  Support more blockchains
    * Hyperledger Fabric
    * Quorum
    * ...

    
## Needed Python packages (apart from standard packages)
     
* boto3  
* scp   
* paramiko 
* web3   
* pytz     
* numpy 
* toml

# Install BlockFormation via pip

The first step is to generate distribution packages for the package:
(you need to be in the directory of setup.py)
```
python setup.py sdist bdist_wheel

```
If this was successful you can install the package with pip. The following is a example if you want to install a pip package for your anaconda env:


```
/anaconda3/envs/aws_automisation/bin/pip install dist/BlockchainFormation-0.0.1.tar.gz 

```

Now you can import the modules like vm_handler:
```
from BlockchainFormation import vm_handler
```