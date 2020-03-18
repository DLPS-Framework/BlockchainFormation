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

  sudo add-apt-repository ppa:deadsnakes/ppa -y
	sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 68DB5E88 || echo "Adding keyserver failed" >> /home/ubuntu/upgrade_fail2.log
	sudo add-apt-repository "deb https://repo.sovrin.org/deb xenial master"
  sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb xenial stable"
  sudo add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu xenial main universe"
	sudo apt-get update

  sudo apt-get install -y libsodium18
    sudo apt-get install -y python3.5 python3-pip python3.5-dev
	sudo apt-get install -y libindy libindy-crypto=0.4.5
	sudo pip3 install python3-indy==1.11.0

  sudo mkdir /etc/indy /var/log/indy /var/lib/indy /var/lib/indy/backup /var/lib/indy/plugins
  sudo chown -R ubuntu:ubuntu /var/log/indy/ /var/lib/indy/ /etc/indy/

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF