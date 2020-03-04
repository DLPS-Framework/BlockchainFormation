# BlockchainFormation

## General Information

The purpose of this script is to automate the process of deploying blockchain solutions on AWS.
This process includes starting ```x``` EC2 instances, installing necessary packages and configuring the virtual machines.
The provided VMs then can be used for example to evaluate the performance of a given blockchain solution, 
or to further customize an implementation for a use case.
If the network is not needed anymore, the script provides a function to shutdown all started VMs after pulling log files.
The shutdown script also calculates the AWS costs caused by the uptime of the virtual machines using the AWS pricing API.

 *NOTE THAT THE CREATED BLOCKCHAIN NODES ARE NOT CONFIGURED WITH HIGH SECURITY SETTINGS* 
## How to run it
This script can either be started by using the argpass CLI or by installing the pip package (see end of this README)

```run.py``` provides an argpass CLI for starting and terminating VMs. 

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
...
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

where the config file will be located in the experiment's directory. The path to this directory will also be displayed in the logs during the blockchain startup.

## How to add another blockchain?
To add another blockchain 4, the following steps are required:
* specific user data script in ```/UserDataScripts```
* add specific startup function in ```vm_handler.py```
* add specific shutdown function in ```vm_handler.py```
* adjustments of argpass CLI and config in ```run.py```
* specific startup/shutdown functionality in e.g. ```/blockchain_specifics/Geth.py```
* (recommended) restart function in e.g. ```/blockchain_specifics/Geth.py```
* add the created directories to [MANIFEST.in](MANIFEST.in)


## Future Steps
* Add Windows support
* Add option to attach no storage at all
* Make existing setups even more customizable
* Add logrotate to UserData setup scripts
*  Support more blockchains
    * Corda
    * Ethermint
    * Libra
    * Tezos

    
## Complete list of needed Python packages (apart from standard packages)
     
See [requirements.txt](requirements.txt)

# Install BlockFormation via pip

The first step is to generate distribution packages for the package 
(you need to be in the directory of setup.py):
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