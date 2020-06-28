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

  sudo apt-get install -y g++ gcc libc6-dev libffi-dev libgmp-dev make zlib1g-dev

  cd /data
  git clone https://github.com/input-output-hk/cardano-sl.git
  cd cardano-sl && git checkout master

  # getting nix
  sh <(curl https://nixos.org/nix/install) --daemon

  sudo echo '
substituters         = https://hydra.iohk.io https://cache.nixos.org
trusted-substituters =
trusted-public-keys  = hydra.iohk.io:f/Ea+s+dFdN+3Y/G+FDgSq+a5NEWhJGzdjvKNGv0/EQ= cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY='
>> /etc/nix/nix.conf

  systemctl restart nix-daemon

  nix-build -A cardano-sl-node-static --out-link master

  ls master/bin

  curl -ssl https://get.haskellstack.org/ | sh
  stack setup
  stack install cpphs
  sudo apt-get install librocksdb-dev

  cd cardano-sl && ./scripts/build/cardano-sl.sh

  echo "export PATH=/home/ubuntu/.local/bin:$PATH" >> ~/.profile

  cd /data
  git clone https://github.com/jemalloc/jemalloc.git
  cd jemalloc && ./configure
  make
  make install

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF