#!/bin/bash -xe

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


  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  # sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88
  sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 68DB5E88 || echo "Adding first keyserver failed" >> /home/ubuntu/upgrade_fail2.log
  sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88 || echo "Adding second keyserver failed" >> /home/ubuntu/upgrade_fail2.log
  sudo apt-get update
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

  git clone https://github.com/hyperledger/indy-node
  (cd indy-node && sudo pip3 install --upgrade pip && sudo pip3 install -e .[tests] && sudo pip3 install flake8 || echo "\n\n=========\nError in indy-node installation\n========\n\n")

  sudo mkdir /etc/indy /var/log/indy /data/indy /data/indy/backup /data/indy/plugins
  sudo chown -R ubuntu:ubuntu /var/log/indy/ /data/indy/ /etc/indy/

  printf "# Current network
NETWORK_NAME = 'mynet'

# Disable stdout logging
enableStdOutLogging = True

# Directory to store ledger.
LEDGER_DIR = '/data/indy'

# Directory to store logs.
LOG_DIR = '/var/log/indy'

# Directory to store keys.
KEYS_DIR = '/data/indy'

# Directory to store genesis transactions files.
GENESIS_DIR = '/data/indy'

# Directory to store backups.
BACKUP_DIR = '/data/indy/backup'

# Directory to store plugins.
PLUGINS_DIR = '/data/indy/plugins'

# Directory to store node info.
NODE_INFO_DIR = '/data/indy'

# Current network
NETWORK_NAME = 'my-net'

# Disable stdout logging
enableStdOutLogging = True

# Directory to store ledger.
LEDGER_DIR = '/data/indy'

# Directory to store logs.
LOG_DIR = '/var/log/indy'

# Directory to store keys.
KEYS_DIR = '/data/indy'

# Directory to store genesis transactions files.
GENESIS_DIR = '/data/indy'

# Directory to store backups.
BACKUP_DIR = '/data/indy/backup'

# Directory to store plugins.
PLUGINS_DIR = '/data/indy/plugins'

# Directory to store node info.
NODE_INFO_DIR = '/data/indy'
" >> /etc/indy/indy_config.py

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF