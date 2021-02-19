#!/bin/bash -xe

#  Copyright 2021 ChainLab
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

  sudo apt-get install -y make || sudo apt-get install -y make
  sudo apt install -y g++ || sudo apt install -y g++
  sudo apt install -y python2.7 python-pip || sudo apt install -y python2.7 python-pip

  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
  . ~/.nvm/nvm.sh
  . ~/.profile
  . ~/.bashrc

  nvm install 8.16.0
  echo "export PATH=$PATH:/home/ubuntu/.nvm/versions/node/v8.16.0/bin" >> /home/ubuntu/.profile
  . ~/.profile
  . ~/.bashrc
  echo "node version: $(node -v)"
  echo "npm version: $(npm -v)"

  # Install requirements for installing crypto stuff
  sudo apt-get install -y cmake autoconf libtool curl python3 pkg-config libssl-dev

  # Install Rust
  curl -sSf https://sh.rustup.rs | sh -s -- -y && source ~/.cargo/env

  # Download and build libsodium
  curl -fsSL https://github.com/jedisct1/libsodium/archive/1.0.18.tar.gz | tar -xz
  cd libsodium-1.0.18 && ./autogen.sh && ./configure --disable-dependency-tracking && make
  echo "export SODIUM_LIB_DIR=/usr/local/lib" >> /home/ubuntu/.profile && . ~/.profile
  echo "export LD_LIBRARY_PATH=/usr/local/lib" >> /home/ubuntu/.profile && . ~/.profile

  # Download and build ursa
  cd /home/ubuntu && git clone https://github.com/hyperledger/ursa.git
  cd /home/ubuntu/ursa/ && cargo build --release
  echo "export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib:/home/ubuntu/ursa/target/release" >> /home/ubuntu/.profile && . ~/.profile
  sudo cp /home/ubuntu/ursa/target/release/*.so /usr/lib

  # Get Indy stuff from Sovrin
  sudo add-apt-repository ppa:deadsnakes/ppa -y
	sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 68DB5E88 || echo "Adding keyserver failed" >> /home/ubuntu/upgrade_fail2.log
	sudo add-apt-repository "deb https://repo.sovrin.org/deb xenial master"
  sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb xenial stable"
  sudo add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu xenial main universe"
	sudo apt-get update

  sudo apt-get install -y python3.5 python3-pip python3.5-dev
	sudo apt-get install -y libindy libindy-crypto=0.4.5
	sudo pip3 install python3-indy==1.11.0

  sudo mkdir /etc/indy /var/log/indy /var/lib/indy /var/lib/indy/backup /var/lib/indy/plugins
  sudo chown -R ubuntu:ubuntu /var/log/indy/ /var/lib/indy/ /etc/indy/

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF