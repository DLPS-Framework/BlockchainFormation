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

   # Installing nvm, node.js and npm
  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
  . ~/.nvm/nvm.sh
  . ~/.profile
  . ~/.bashrc

  nvm install 13.12.0
  echo "export PATH=$PATH:/home/ubuntu/.nvm/versions/node/v13.12.0/bin" >> /home/ubuntu/.profile
  . ~/.profile
  . ~/.bashrc
  echo "node version: $(node -v)"
  echo "npm version: $(npm -v)"
  # for installing truffle/contract
  echo "nvm version: $(nvm version)"
  sudo apt update


  # Installing tezos alphanet
  sudo apt-get update \
&& sudo apt-get upgrade \
&& sudo apt install -y rsync git m4 build-essential patch unzip bubblewrap wget pkg-config libgmp-dev libev-dev libhidapi-dev ntp rng-tools\
&& echo "HRNGDEVICE=/dev/urandom" | sudo tee -a /etc/default/rng-tools \
&& /etc/init.d/rng-tools start \
&& wget https://github.com/ocaml/opam/releases/download/2.0.5/opam-2.0.5-x86_64-linux \
&& sudo cp opam-2.0.5-x86_64-linux /usr/local/bin/opam \
&& sudo chmod a+x /usr/local/bin/opam \
&& git clone https://gitlab.com/tezos/tezos.git \
&& cd tezos \
&& git checkout carthagenet \
&& sed -i -e 's/edpkugeDwmwuwyyD3Q5enapgEYDxZLtEUFFSrvVwXASQMVEqsvTqWu/edpkuSLWfVU1Vq7Jg9FucPyKmma6otcMHac9zG4oU1KMHSTBpJuGQ2/g' /home/ubuntu/tezos/src/proto_genesis/lib_protocol/data.ml \
&& sed -i -e 's/edpktiJknwZ8rQkkZdQUBVmG8Goau6C6JBTMX1hohxMGsQAG1qfFze/edpkuSLWfVU1Vq7Jg9FucPyKmma6otcMHac9zG4oU1KMHSTBpJuGQ2/g' /home/ubuntu/tezos/src/proto_genesis/lib_protocol/data.ml \
&& opam init -a \
&& opam switch create tezos ocaml-base-compiler.4.07.1 \
&& eval $(opam env) \
&& export PATH=/home/ubuntu/tezos/_opam/bin/:$PATH \
&& make build-deps \
&& eval $(opam env) \
&& export PATH=/home/ubuntu/tezos/_opam/bin/:$PATH \
&& make \
&& ~/tezos/tezos-node identity generate --data-dir ~/test

printf '#/bin/bash

ADDR=\$1

ACTIVATOR_SECRET="unencrypted:edsk31vznjHSSpGExDMHYASz45VZqXN4DPxvsa4hAyY8dHM28cZzp6"
~/tezos/tezos-client --addr \$ADDR --port 18730 import secret key activator \${ACTIVATOR_SECRET}
~/tezos/tezos-client --addr \$ADDR --port 18730 -block genesis activate protocol PsCARTHAGazKbHtnKfLzQg3kms52kSRpgnDY982a9oYsSXRLQEb with fitness 1 and key activator and parameters ~/tezos/sandbox-parameters.json --timestamp \$(TZ="AAA+1" date +%%FT%%TZ)
' >> ~/bootstrap.sh && sudo chmod 775 ~/bootstrap.sh

cd ~
git clone https://github.com/claudebarde/tezos-react-tutorial

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF