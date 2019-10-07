# BlockchainFormation

## Major Updates:
 * *July 22 2019:* Added Quorum/Fabric/Sawtooth Support (WIP)
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
This script can either be started by using the argpass CLI or by installing the pip package (see end of this README)

```run.py``` provides a argpass CLI for starting and terminating VMs. 

* Start a private Geth Network with PoA consensus: 


```
python run.py start geth --vm_count 4 --instance_type t2.micro --priv_key_path ~/.ssh/blockchain --tag_name blockchain_philipp 
--subnet_id subnet-123 --security_group_id sg-123 --aws_credentials ~/.aws/credentials --aws_config ~/.aws/config 
--profile block_exp --key_name blockchain  --VolumeSize 32 --chainid 11
```
__This is an example for a run command, values need to be adjusted for your config__

* Start a Base Network where __NO__ blockchain frameworks will be installed, just x VMs with the base installations (e.g. proxy)


```
python run.py start base --vm_count 4 --instance_type t2.micro --priv_key_path ~/.ssh/blockchain --tag_name test_networtk 
--subnet_id subnet-123 --security_group_id sg-132 --aws_credentials ~/.aws/credentials --aws_config ~/.aws/config 
--profile block_exp --key_name blockchain  --VolumeSize 32
```
__This is an example for a run command, values need to be adjusted for your config__


Explanation of flags can be obtained by typing e.g.:
```
python run.py start geth --help
python run.py start base --help
python run.py start parity --help
```

__Note that you need to enter the password for your proxy user after starting the script__


*If you do not want to create the large CLI every time you can also  start a network with a given config file:*
```
python run.py start --config "path to config file" 
```
Example config files are provided in ```/example_config_files/base_config.json```

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
* Support the new aws proxies (proxy.ccc-ng-1.eu-central-1.aws.cloud.bmw.)
* Add InstanceMarketOptions for cheaper VMs (Does the AWS Calculator take care of this?)
* Add Windows support
* Add option to attach no storage at all
* Make geth/parity setup even more customizable
* Add logrotate to UserData setup scripts
*  Support more blockchains
    * Libra
    * Corda
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


## License

[Apache License 2.0](LICENSE)