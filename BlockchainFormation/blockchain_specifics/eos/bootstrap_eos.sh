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
  sudo apt-get -y upgrade

  # Getting curl
  sudo apt install curl

  # Installing docker for improved port exposure in a swarm
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

  sudo apt-get install -y clang cmake unzip jq

  # Getting the compiled binaries
  # wget https://github.com/EOSIO/eos/releases/download/v2.0.3/eosio_2.0.3-1-ubuntu-18.04_amd64.deb
  # sudo apt install -y ./eosio_2.0.3-1-ubuntu-18.04_amd64.deb

  # In case we want to modify parameters such as blocktime, we need to build the binaries from source
  # https://developers.eos.io/manuals/eos/latest/install/build-from-source/index
  # Note that this is only possible with >= 8GB of RAM, so we need at least a m5.large instance to do this

  # sudo apt-get install -y make

  # mkdir -p /data/eosio && cd /data/eosio
  # git clone --recursive https://github.com/EOSIO/eos
  # cd eos && git pull --recurse-submodules && git submodule update --init --recursive
  # cd /data/eosio/eos && yes | ./scripts/eosio_build.sh

  # this can actually take an hour!
  # cd /data/eosio/eos/build && sudo make install && make test

  # Do not remove - gets substituted by the commands for using prebuilt binaries or building binaries from scratch
  substitute_replace_command

  # In case we use standard settings, we can download the binaries directly
  wget https://github.com/EOSIO/eosio.cdt/releases/download/v1.6.3/eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb
  sudo apt install -y ./eosio.cdt_1.6.3-1-ubuntu-18.04_amd64.deb

  wget https://github.com/EOSIO/eosio.contracts/archive/v1.8.1.zip
  unzip v1.8.1.zip
  mv eosio.contracts-1.8.1 ~/contracts

  mkdir /data/bootbios
  cd /data/bootbios
  mkdir genesis

  printf '{
  "initial_timestamp": "2019-03-012T08:55:11.000",
  "initial_key": "EOS_PUB_DEV_KEY",
  "initial_configuration": {
    "max_block_net_usage": 1048576,
    "target_block_net_usage_pct": 1000,
    "max_transaction_net_usage": 524288,
    "base_per_transaction_net_usage": 12,
    "net_usage_leeway": 500,
    "context_free_discount_net_usage_num": 20,
    "context_free_discount_net_usage_den": 100,
    "max_block_cpu_usage": 100000,
    "target_block_cpu_usage_pct": 500,
    "max_transaction_cpu_usage": 50000,
    "min_transaction_cpu_usage": 100,
    "max_transaction_lifetime": 3600,
    "deferred_trx_expiration_window": 600,
    "max_transaction_delay": 3888000,
    "max_inline_action_size": 4096,
    "max_inline_action_depth": 4,
    "max_authority_depth": 6
  },
  "initial_chain_id": "0000000000000000000000000000000000000000000000000000000000000000"
}
' >> genesis.json

  cd genesis

  printf '#!/bin/bash

DATADIR="./blockchain"
if [ ! -d \$DATADIR ]; then
  mkdir -p \$DATADIR;
fi

nodeos \
--genesis-json \$DATADIR"/../../genesis.json" \
--signature-provider EOS_PUB_DEV_KEY=KEY:EOS_PRIV_DEV_KEY \
--plugin eosio::producer_plugin \
--plugin eosio::producer_api_plugin \
--plugin eosio::chain_plugin \
--plugin eosio::chain_api_plugin \
--plugin eosio::http_plugin \
--plugin eosio::history_api_plugin \
--plugin eosio::history_plugin \
--data-dir \$DATADIR"/data" \
--blocks-dir \$DATADIR"/blocks" \
--config-dir \$DATADIR"/config" \
--producer-name substitute_producer_name \
--http-server-address 0.0.0.0:8888 \
--p2p-listen-endpoint 0.0.0.0:4444 \
--access-control-allow-origin=* \
--contracts-console \
--http-validate-host=false \
--verbose-http-errors \
--enable-stale-production \
substitute_peers\
>> \$DATADIR"/nodeos.log" 2>&1 & \
echo \$! > \$DATADIR"/eosd.pid"
' >> genesis_start.sh

  printf '#!/bin/bash

DATADIR="./blockchain"
if [ ! -d \$DATADIR ]; then
  mkdir -p \$DATADIR;
fi

nodeos \
--signature-provider EOS_PUB_DEV_KEY=KEY:EOS_PRIV_DEV_KEY \
--plugin eosio::producer_plugin \
--plugin eosio::producer_api_plugin
--plugin eosio::chain_plugin \
--plugin eosio::chain_api_plugin \
--plugin eosio::http_plugin \
--plugin eosio::history_api_plugin \
--plugin eosio::history_plugin \
--data-dir \$DATADIR"/data" \
--blocks-dir \$DATADIR"/blocks" \
--config-dir \$DATADIR"/config" \
--producer-name substitute_producer_name \
--http-server-address 0.0.0.0:8888 \
--p2p-listen-endpoint 0.0.0.0:4444 \
--access-control-allow-origin=* \
--contracts-console \
--http-validate-host=false \
--verbose-http-errors \
--enable-stale-production \
substitute_peers\
>> \$DATADIR"/nodeos.log" 2>&1 & \
echo \$! > \$DATADIR" /eosd.pid"
' >> start.sh

  printf '#!/bin/bash

DATADIR="./blockchain/"
if [ -f \$DATADIR"/eosd.pid" ]; then
  pid=`cat \$DATADIR"/eosd.pid"`
  echo \$pid
  kill \$pid
  rm -r \$DATADIR"/eosd.pid"
  echo -ne "Stoping Node"
  while true; do
    [ ! -d "/proc/\$pid/fd" ] && break
    echo -ne "."
    sleep 1
  done
  echo -ne "\rNode Stopped. \n"
fi
' >> stop.sh

  printf '#!/bin/bash

rm -fr blockchain
ls -al
' >> clean.sh

  sudo chmod +x *.sh

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF