# EC2 Automation Script

## General Information

The purpose of this script is to automate the process of deploying blockchain solutions on aws.
This process includes starting X ec2 instances, installing necessary packages and configure the virtual machines.
The provided VMs then can used for example to evaluate the performance of a given blockchain solution.
If the network is not needed anymore, the script provides  a function to shutdown all started VMs after pulling log files.
The shutdown script also calculates the aws costs caused by the uptime of the virtual machines using the aws pricing API.

## How to run it

```run.py``` provides a argpass CLI for starting and terminating VMs.

* Start a VM Network:
```
python run.py start --vm_count 4 --instance_type t2.micro --blockchain_type geth --ssh_key ~/.ssh/blockchain --tag blockchain_philipp 
--subnet subnet-0ac7aeeec87150dd7 --security_group sg-0db312b6f84d66889 --aws_credentials ~/.aws/credentials --aws_config ~/.aws/config 
--profile block_exp --key_name blockchain --image_id ami-0366f703a7edcf070 --storage 32 --proxy_user qqdpoc0
```
```
  --vm_count VM_COUNT, -vmc VM_COUNT
                        specify how many VM you want to start
  --instance_type {t2.nano,t2.micro,t2.small,t2.medium,t2.large,t2.xlarge,t2.2xlarge}, -it {t2.nano,t2.micro,t2.small,t2.medium,t2.large,t2.xlarge,t2.2xlarge}
                        specify what type of instances you want to start
  --blockchain_type {geth}, -bt {geth}
                        which network to setup (at the moment only geth)
  --aws_credentials AWS_CREDENTIALS, -cred AWS_CREDENTIALS
                        path to aws credentials
  --key_name KEY_NAME, -kn KEY_NAME
                        name of aws credentials key
  --aws_config AWS_CONFIG, -aws_con AWS_CONFIG
                        path to aws config
  --ssh_key SSH_KEY, -key SSH_KEY
                        path to ssh key
  --image_id IMAGE_ID, -img_id IMAGE_ID
                        image ID for vm (default is to get newest ubuntu 18
                        build)
  --storage {1,2,3}, -s {1,2,3}
                        amount of extra storage in GB
  --profile PROFILE, -p PROFILE
                        name of aws profile
  --tag TAG, -t TAG     tag for aws
  --subnet SUBNET, -st SUBNET
                        subnet id
  --security_group SECURITY_GROUP [SECURITY_GROUP ...], -sg SECURITY_GROUP [SECURITY_GROUP ...]
                        security group, multiple values allowed
  --proxy_user PROXY_USER, -pu PROXY_USER
                        enter q number for proxy
```
* Terminate a VM Network:

```
python run.py terminate --config "path to config file" 
```

## How to add another blockchain?
To add another blockchain 4 things need to be added:
* specific startup function in ```vm_handler.py```
* specific shutdown function in ```vm_handler.py```
* adjustments of argpass CLI and config in ```vrun.py```
* specific user data script in ```/UserDataScripts```

## Future Steps

*  Support more blockchains
    * Parity
    * Hyperledger Fabric
    * ...