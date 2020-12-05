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

  # Install requirements for installing crypto stuff
  sudo apt-get install -y cmake autoconf libtool curl python3 pkg-config libssl-dev python3-pip

  # Install Rust
  curl -sSf https://sh.rustup.rs | sh -s -- -y && source ~/.cargo/env

  # Download and build libsodium
  curl -fsSL https://github.com/jedisct1/libsodium/archive/1.0.18.tar.gz | tar -xz
  cd libsodium-1.0.18 && ./autogen.sh && ./configure --disable-dependency-tracking && make
  echo "export SODIUM_LIB_DIR=/usr/local/lib" >> /home/ubuntu/.profile && . ~/.profile
  echo "export LD_LIBRARY_PATH=/usr/local/lib" >> /home/ubuntu/.profile && . ~/.profile

  # Download and build ursa
  cd /home/ubuntu && git clone https://github.com/hyperledger/ursa.git
  cd /home/ubuntu/ursa/ && git checkout d31d6634d039c05cba91aa52d8710f7fe2e5113e && cargo build --release # git checkout b10f0f973b3517d878d640dcd90cfc83ae1b4c93 &&
  echo "export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib:/home/ubuntu/ursa/target/release" >> /home/ubuntu/.profile && . ~/.profile
  sudo cp /home/ubuntu/ursa/target/release/*.so /usr/lib

  # Get Indy stuff from Sovrin
  # sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88
  sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 68DB5E88 || echo "Adding first keyserver failed" >> /home/ubuntu/upgrade_fail2.log
  sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88 || echo "Adding second keyserver failed" >> /home/ubuntu/upgrade_fail2.log
  sudo apt-get update
  sudo add-apt-repository "deb https://repo.sovrin.org/deb bionic master"
  sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb bionic stable"
  sudo add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu bionic main universe"
  sudo add-apt-repository ppa:deadsnakes/ppa -y
  sudo apt-get update

  sudo apt-get install -y apt-transport-https ca-certificates
  # sudo apt-get install -y libsodium-dev
  sudo apt-get install -y libbz2-dev zlib1g-dev liblz4-dev libsnappy-dev #rocksdb=5.8.8
  sudo apt-get install -y librocksdb-dev
  sudo apt-get install -y software-properties-common
  sudo apt-get install -y python3.5 python3-pip python3.5-dev
  # sudo python3 -m pip install --upgrade pip

  sudo apt-get install -y libindy # libindy-crypto=0.4.*

  sudo apt-get update
  sudo apt-get install apt-transport-https ca-certificates
  apt-key adv --keyserver keyserver.ubuntu.com --recv-keys CE7709D068DB5E88
  sudo add-apt-repository "deb https://repo.sovrin.org/deb xenial master"
  sudo apt-get update
  sudo apt-get install libindy-crypto

  cd
  git clone https://github.com/hyperledger/indy-node
  # sed -i 's/indy-plenum==1.13.0.dev1024/indy-plenum==1.12.4/g' /home/ubuntu/indy-node/setup.py
  (cd indy-node && sudo pip3 install --upgrade pip && (sudo pip3 install . ; sudo pip3 install . ) && sudo pip3 install flake8 || echo "\n\n=========\nError in indy-node installation\n========\n\n")

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