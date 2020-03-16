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

  cd

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in quorum_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  # Setting up go (TODO: check whether go is necessary)
  # echo 'Y' | sudo apt-get install golang-go
  wget -c https://dl.google.com/go/go1.13.8.linux-amd64.tar.gz
  sudo tar -C /usr/local -xzf go1.13.8.linux-amd64.tar.gz -C /usr/local

  echo "export GOROOT=\"/usr/local/go\"" >> ~/.profile
  echo "export GOPATH=\"/usr/local/go/bin\"" >> ~/.profile
  echo "export PATH=\"\$PATH:\$GOPATH\"" >> ~/.profile
  echo "export GO111MODULE=on" >> ~/profile

  source ~/.profile

  sudo chown -R ubuntu:ubuntu /usr/local/go

  sudo apt-get install -y build-essential
  git clone https://github.com/ethereum/go-ethereum
  cd go-ethereum
  make geth

  mkdir -p $GOPATH/src/github.com/tendermint
  cd $GOPATH/src/github.com/tendermint
  git clone https://github.com/tendermint/tendermint.git
  cd tendermint
  make tools
  make install

  mv build/tendermint $GOPATH/bin

  tendermint --home ~/.ethermint/tendermint init
  tendermint --home ~/.ethermint/tendermint node

  mkdir -p $GOPATH/src/github.com/cosmos
  cd $GOPATH/src/github.com/cosmos

  git clone https://github.com/cosmos/ethermint.git
  cd ethermint
  make tools
  make

  # ethermint --datadir ~/.ethermint --rpc --rpcaddr=0.0.0.0 ws --wsaddr=0.0.0.0 --rpcapi eth,net,web3,personal,admin


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF