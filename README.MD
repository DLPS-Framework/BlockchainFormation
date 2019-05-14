# EC2 Automation Script

## General Information

The purpose of this script is to automate the process of deploying blockchain solutions on aws.
This process includes starting X ec2 instances, installing necessary packages and configure the virtual machines.
The provided VMs then can used for example to evaluate the performance of a given blockchain solution.
If the network is not needed anymore, the script provides  a function to shutdown all started VMs after pulling log files.
The shutdown script also calculates the aws costs caused by the uptime of the virtual machines using the aws pricing API.

## How to run it

```run.py``` provides a argpass CLI for starting and terminating VMs.

* Start a Geth Network: 


```
python run.py start geth --vm_count 4 --instance_type t2.micro --ssh_key ~/.ssh/blockchain --tag blockchain_philipp 
--subnet subnet-0ac7aeeec87150dd7 --security_group sg-0db312b6f84d66889 --aws_credentials ~/.aws/credentials --aws_config ~/.aws/config 
--profile block_exp --key_name blockchain  --storage 32 --proxy_user qqdpoc0
```
__This is an example  for a run command, values need to be adjusted for your config__


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
  --ssh_key SSH_KEY, -key SSH_KEY
                        path to ssh key [default=~.ssh/blockchain]
  --image_id IMAGE_ID, -img_id IMAGE_ID
                        image ID for vm [default=None (the script then pulls newest ubuntu 18 img)]
  --storage STORAGE, -s STORAGE
                        amount of extra storage in GB: min 8, max 1024 [default=32]
  --profile PROFILE, -p PROFILE
                        name of aws profile [default=block_exp]
  --tag TAG, -t TAG     tag for aws [default=blockchain_experiment]
  --subnet SUBNET, -st SUBNET
                        subnet id [default=subnet-0ac7aeeec87150dd7]
  --security_group SECURITY_GROUP [SECURITY_GROUP ...], -sg SECURITY_GROUP [SECURITY_GROUP ...]
                        security group, multiple values allowed [default=sg-0db312b6f84d66889]
  --proxy_user PROXY_USER, -pu PROXY_USER
                        enter q number for proxy [default=qqdpoc0]
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

```
__Note that you need to enter the password for your proxy user after starting the script__

* Terminate a VM Network:

```
python run.py terminate --config "path to config file" 
```

## How to add another blockchain?
To add another blockchain 4 things need to be added:
* specific startup function in ```vm_handler.py```
* specific shutdown function in ```vm_handler.py```
* adjustments of argpass CLI and config in ```run.py```
* specific user data script in ```/UserDataScripts```

## Future Steps
* Make geth setup more customizable
*  Support more blockchains
    * Parity
    * Hyperledger Fabric
    * ...