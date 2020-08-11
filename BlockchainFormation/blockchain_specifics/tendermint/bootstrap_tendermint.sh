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


  cd /data
  sudo chown -R ubuntu /data

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in ethermint_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  # Setting up go (TODO: check whether go is necessary)
  # echo 'Y' | sudo apt-get install golang-go
  wget -c https://dl.google.com/go/go1.13.8.linux-amd64.tar.gz
  sudo tar -C /usr/local -xzf go1.13.8.linux-amd64.tar.gz
  sudo chown -R ubuntu:ubuntu /usr/local

  echo "export GOROOT=/usr/local/go" >> ~/.profile
  echo "export GOPATH=/usr/local/go/bin" >> ~/.profile
  echo "export PATH=$PATH:/usr/local/go:/usr/local/go/bin:/usr/local/go/bin/bin:/home/ubuntu/.nvm/versions/node/v8.16.0/bin" >> ~/.profile
  echo "export GO111MODULE=on" >> ~/.profile

  . ~/.profile

  sudo apt-get install -y gcc jq make

  git clone https://github.com/tendermint/tendermint.git
  cd tendermint
  make tools
  make install
  make build

# Getting curl
  sudo apt install curl

  # Installing docker
  sudo apt-get update
  sudo apt-get install -y apt-transport-https ca-certificates gnupg-agent software-properties-common
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io

  # Installing docker-compose
  sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  # Testing the installation
  docker-compose --version

  # Eventually user permissions need to be adjusted... rebooting required!
  sudo usermod -aG docker ubuntu
  newgrp docker

  # Installing nvm, node.js and npm
  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
  . ~/.nvm/nvm.sh
  . ~/.profile
  . ~/.bashrc

  nvm install 8.16.0
  echo "node version: $(node -v)"
  echo "npm version: $(npm -v)"
  echo "nvm version: $(nvm version)"
  sudo apt update


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF