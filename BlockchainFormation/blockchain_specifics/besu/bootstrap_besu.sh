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
  sudo apt-get -y upgrade || echo "Upgrading in quorum_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log


  sudo apt-get install -y jq


  # Installing Java 11
  sudo apt install openjdk-11-jdk -y


  # Getting besu binaries and adding them to path
  wget -c https://bintray.com/hyperledger-org/besu-repo/download_file?file_path=besu-1.4.3.tar.gz
  sudo tar -xvzf 'download_file?file_path=besu-1.4.3.tar.gz' && rm -rf 'download_file?file_path=besu-1.4.3.tar.gz'

  echo "export PATH=$PATH:/data/besu-1.4.3/bin" >> /home/ubuntu/.profile


  mkdir IBFT-Network && cd IBFT-Network

  echo '
{
 "genesis": {
   "config": {
      "chainId": 2018,
      "constantinoplefixblock": 0,
      "ibft2": {
        "blockperiodseconds": substitute_period,
        "epochlength": 30000,
        "requesttimeoutseconds": 5
      }
    },
    "nonce": "0x0",
    "timestamp": "0x58ee40ba",
    "gasLimit": "0xE0000000",
    "difficulty": "0x1",
    "mixHash": "0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365",
    "coinbase": "0x0000000000000000000000000000000000000000",
    "alloc": {
       "substitute_address": {
         "balance": "90000000000000000000000"
       }
    }
 },
 "blockchain": {
   "nodes": {
     "generate": true,
       "count": substitute_count
   }
 }
}
' > ibftConfigFile.json


  printf '#/bin/bash

for i in {0..substitute_count}; do
  mkdir "/data/IBFT-Network/Node_\$i"
  cd "/data/IBFT-Network/Node_\$i"
  cp /data/IBFT-Network/networkFiles/genesis.json .
  mkdir data
done

i=0
for d in /data/IBFT-Network/networkFiles/keys/*/; do
  echo "\$d"
  mv "\$d"* /data/IBFT-Network/Node_"\$i"/data
  i=\$(( \$i + 1 ))
done
' >> /data/make_dirs.sh

  sudo chmod 777 /data/make_dirs.sh



  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF