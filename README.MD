# BlockchainFormation

## General Information

The purpose of this package is to automate the process of deploying blockchain solutions. It is currently supported on AWS or on fresh, own ubuntu 18.04 VMs.
Everything happens via ssh and scp (wrapped in python), orchestrated from the computer where this package is installed.

In the beginning, one has to specify the configuration of the blockchain network, e.g. number of nodes, blocksize, ..., by means of a config file.
In case of AWS setup, AWS settings have to be included, based on which ```vm_count``` EC2 instances will automatically be started. Afterwards, necessary software packages will be installed on each VM, 
and a blockchain network with the specified configuration will be automatically be orchestrated on the virtual machines, organized centrally from the computer where the package *BlockchainFormation* is used.

Currently, the following blockchains are supported:
* Corda (beta)
* Eos (beta)
* Hyperledger Fabric (very sophisticated)
* Ethereum with Geth and Parity client (very sophisticated)
* Hyperledger Indy (sophisticated)
* Quorum with RAFT and IBFT consensus (very sophisticated)
* Hyperledger Sawtooth (very sophisticated)
* Tezos (beta)

In order to have some baseline, we also integrated
* CouchDB (beta)
* LevelDB (alpha)

The provided VMs then can be used for different objectives, e.g., to deploy custom smart contracts and connect with clients (see package *ClientFormation*) and then do some benchmarking (see package *ChainLab*), i.e., 
to evaluate the performance of a given blockchain solution, 
Another possibility is to further customize an implementation for a specific use case.

If the network is not needed anymore and the VMs have been started via AWS, the script provides a function to shutdown all started VMs after pulling log files.
The shutdown script also calculates the AWS costs caused by the uptime of the virtual machines using the AWS pricing API.

 *!!! NOTE THAT THE CREATED BLOCKCHAIN NODES ARE NOT CONFIGURED WITH **ANY** SECURITY SETTINGS* !!!
 
 In particular, while prototyping based on the scripts in this repository is fine, all setups should **never** be used in production.  
## How to run it
The functionalities can either be started by using the argpass CLI (```run.py```) or by installing the pip package (see end of this README)
The argpass CLI be provided with a config file:

* Start a network
```
python run.py start --config "path to config file" 
```
Example config files are provided in ```/example_config_files/aws_configs``` (with aws) and ```/example_config_files/own_configs``` (with given VMs). 

* Terminate a network:

```
python run.py terminate --config "path to config file" 
```

where the config file will be located in the experiment's directory. The path to this directory will also be displayed in the logs during the blockchain startup.

## How to add another blockchain?
To add another blockchain, the following steps are required:
* create a directory ```/blockchain_specifics/Blockchain``` containing
  + a Bash script for the basic installations, i.e. ```/blockchain_specifics/blockckain/bootstrap_blockchain.sh```
  + a Python file with a specific startup, shutdown (, and restart) functionality, i.e. ```/blockchain_specifics/blockchain/blockchain.py```.  
  Within the startup functionality, the following keys should be added to the config file if the blockchain is meant to be benchmarked later on:
    - 'node_indices': which of the VMs should be considered as nodes? There might be VMs which are rather of auxiliary type, e.g., Notaries in Corda or CAs in Hyperleder Fabric
    - 'groups': a partitioning of the nodes e.g. by geographical distribution, for setting delays or package losses later on (perfect connection within a group, worse connection to members of the other groups) 
* add an example config file in ```example_config_files```
* integrate the specific startup and shutdown function in ```vm_handler.py```
* add the created directories to [MANIFEST.in](MANIFEST.in) (pay attention that sometimes recursive inclusion might be needed)


## Future Steps
* Keep everything up to date as blockchains evolve
* Add option to attach no storage at all # TODO??? @Philipp?
* Make existing setups even more customizable
* Add logrotate to UserData setup scripts # TODO??? @Philipp
*  Support more blockchains
    * Ethermint
    * Libra
* Integrate Azure or further cloud computing services
* In-depth explanation of all the blockchain-specific configurations in the configs
* Find a nicer way to modify bootstrap_scripts based on the config file
+ Sophisticated checking of the values specified in config files
* Implement other user names than ```ubuntu```, and other file names than ```data```
* Add Windows support?
    
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
/anaconda3/envs/aws_automisation/bin/pip install dist/BlockchainFormation-1.0.0.tar.gz 

```

Now you can import the modules like vm_handler:
```
from BlockchainFormation import vm_handler
```


## License

[Apache License 2.0](LICENSE)