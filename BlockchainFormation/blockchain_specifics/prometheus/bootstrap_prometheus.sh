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
  sudo apt-get -y upgrade || echo "Upgrading failed" >> /home/ubuntu/upgrade_fail2.log

  # Get and install prometheus
  cd /home/ubuntu
  wget https://github.com/prometheus/prometheus/releases/download/v2.22.0/prometheus-2.22.0.linux-amd64.tar.gz
  tar xvfz prometheus-2.22.0.linux-amd64.tar.gz && mv prometheus-2.22.0.linux-amd64 prometheus
  rm -rf prometheus-2.22.0.linux-amd64.tar.gz

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF