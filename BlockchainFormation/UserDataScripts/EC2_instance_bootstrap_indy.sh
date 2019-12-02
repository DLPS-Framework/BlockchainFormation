#!/bin/bash -xe

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  # sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88
  sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 68DB5E88 || echo "Adding first keyserver failed" >> /home/ubuntu/upgrade_fail2.log
  sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88 || echo "Adding second keyserver failed" >> /home/ubuntu/upgrade_fail2.log
  sudo aot-get update
  sudo add-apt-repository "deb https://repo.sovrin.org/deb xenial master"
  sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb xenial stable"
  sudo add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu xenial main universe"
  sudo add-apt-repository ppa:deadsnakes/ppa -y
  sudo apt-get update

  sudo apt-get install -y apt-transport-https ca-certificates
  sudo apt-get install -y libsodium18
  sudo apt-get install -y libbz2-dev zlib1g-dev liblz4-dev libsnappy-dev rocksdb=5.8.8
  sudo apt-get install -y software-properties-common
  sudo apt-get install -y python3.5 python3-pip python3.5-dev
  sudo apt-get install -y libindy libindy-crypto=0.4.5
  sudo apt-get install -y indy-cli

  # git clone https://github.com/hyperledger/indy-plenum
  git clone https://github.com/hyperledger/indy-node
  (cd indy-node && sudo pip3 install --upgrade pip && sudo pip3 install -e .[tests] && sudo pip3 install flake8 || echo "\n\n=========\nError in indy-node installation\n========\n\n")
  # (cd indy-plenum && sudo pip3 install boto3 && sudo pip3 install asyncio && sudo pip3 install ansible && sudo pip3 install -e .[tests] || echo "\n\n=========\nError in indy-plenum installation\n========\n\n")
  # (cd indy-sdk/samples/python/src && sudo pip3 install -e .[tests]) || echo "\n\n=========\nError in indy-sdk installation\n========\n\n")

  sudo mkdir /etc/indy /var/log/indy /var/lib/indy /var/lib/indy/backup /var/lib/indy/plugins
  sudo chown -R ubuntu:ubuntu /var/log/indy/ /var/lib/indy/ /etc/indy/

  printf "# Current network
NETWORK_NAME = 'mynet'

# Disable stdout logging
enableStdOutLogging = True

# Directory to store ledger.
LEDGER_DIR = '/var/lib/indy'

# Directory to store logs.
LOG_DIR = '/var/log/indy'

# Directory to store keys.
KEYS_DIR = '/var/lib/indy'

# Directory to store genesis transactions files.
GENESIS_DIR = '/var/lib/indy'

# Directory to store backups.
BACKUP_DIR = '/var/lib/indy/backup'

# Directory to store plugins.
PLUGINS_DIR = '/var/lib/indy/plugins'

# Directory to store node info.
NODE_INFO_DIR = '/var/lib/indy'

# Current network
NETWORK_NAME = 'my-net'

# Disable stdout logging
enableStdOutLogging = True

# Directory to store ledger.
LEDGER_DIR = '/var/lib/indy'

# Directory to store logs.
LOG_DIR = '/var/log/indy'

# Directory to store keys.
KEYS_DIR = '/var/lib/indy'

# Directory to store genesis transactions files.
GENESIS_DIR = '/var/lib/indy'

# Directory to store backups.
BACKUP_DIR = '/var/lib/indy/backup'

# Directory to store plugins.
PLUGINS_DIR = '/var/lib/indy/plugins'

# Directory to store node info.
NODE_INFO_DIR = '/var/lib/indy'
" >> /etc/indy/indy_config.py

  # preventing the indy-node process from reaching of open file descriptors limit caused by clients connections
  #	preventing the indy-node process from large memory usage as ZeroMQ creates the separate queue for each TCP connection
  # sudo iptables -I INPUT -p tcp --syn --dport 9702 -m connlimit --connlimit-above 500 --connlimit-mask 0 -j REJECT --reject-with tcp-reset

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF