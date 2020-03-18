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

  # Getting updates and upgrades
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in fabric_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

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

  # Eventually user permissions need to be adjusted... rebooting required!
  sudo usermod -aG docker ubuntu
  newgrp docker

  # Cloning hyperledger fabric + docker images
  curl -sSL http://bit.ly/2ysbOFE | sudo bash -s -- substitute_fabric_version substitute_fabric_ca_version substitute_fabric_thirdparty_version
  docker pull hyperledger/fabric-zookeeper

  # Cloning github repository with helping material for Multi-Host-Network
  git clone https://github.com/wahabjawed/Build-Multi-Host-Network-Hyperledger.git
  sudo mv Build-Multi-Host-Network-Hyperledger fabric-samples

  # Putting fabric bins to path
  echo "export PATH=$PATH:/usr/local/go/bin:/data/fabric-samples/bin" >> /home/ubuntu/.profile
  source ~/.profile

  # Changing permissions for fabric-samples repository
  sudo chown -R ubuntu:ubuntu /data/fabric-samples/

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log
  sudo reboot

EOF