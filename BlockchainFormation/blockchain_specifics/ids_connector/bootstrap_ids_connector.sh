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
  sudo apt-get -y upgrade || echo "Upgrading failed" >> /home/ubuntu/upgrade_fail2.log

  # Installing Java and Maven
  sudo apt-get install -y openjdk-11-jdk
  sudo apt install -y maven

  # Installing docker
  sudo apt-get update
  sudo apt-get install -y apt-transport-https ca-certificates gnupg-agent software-properties-common
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  sudo add-apt-repository -y "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"
  apt-cache policy docker-ce
  sudo apt install -y docker-ce

  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose

  # Eventually user permissions need to be adjusted... rebooting required!
  sudo usermod -aG docker ubuntu
  newgrp docker

  # Cloning the dataspaces repository
  sudo apt-get install -y git
  git clone https://github.com/FraunhoferISST/DataspaceConnector
  echo "export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64/" >> /home/ubuntu/.profile
  . /home/ubuntu/.profile
  cd DataspaceConnector && mvn package


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF