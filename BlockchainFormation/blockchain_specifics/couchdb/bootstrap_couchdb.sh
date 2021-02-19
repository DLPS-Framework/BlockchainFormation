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


  # Getting updates and upgrades
  sudo apt-get update
  sudo apt-get -y upgrade

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

  # Get CouchDB image
  docker pull apache/couchdb:latest

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF