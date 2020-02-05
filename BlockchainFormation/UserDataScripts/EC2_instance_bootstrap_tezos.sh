#!/bin/bash -xe

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
  # Testing the installation
  docker --version
  sudo docker run hello-world

  # Installing docker-compose
  sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
  # Testing the installation
  docker-compose --version

  # Eventually user permissions need to be adjusted... rebooting required!
  sudo usermod -aG docker ubuntu
  newgrp docker
  # Testing whether docker runs without user permissions
  docker run hello-world

  sudo apt install -y gcc
  sudo apt install -y jq
  sudo apt-get install -y make
  sudo apt-get install -y unzip
  sudo apt-get install -y bubblewrap

  sudo apt install -y rsync git m4 build-essential patch unzip bubblewrap wget pkg-config libgmp-dev libev-dev libhidapi-dev which
  wget https://github.com/ocaml/opam/releases/download/2.0.3/opam-2.0.3-x86_64-linux
  sudo cp opam-2.0.3-x86_64-linux /usr/local/bin/opam
  sudo chmod a+x /usr/local/bin/opam
  git clone https://gitlab.com/tezos/tezos.git
  sudo chmod -R 755 /data/tezos

  sudo apt-get install -qq -yy libev-dev libgmp-dev libhidapi-dev m4 perl pkg-config

  (cd /data/tezos; git checkout alphanet; opam init -a)
  export PATH=/data/tezos:$PATH
  source /data/tezos/src/bin_client/bash-completion.sh
  export TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=Y
  (cd /data/tezos; make build-deps)
  export PATH=/data/tezos:$PATH
  export TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=Y


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log
  sudo reboot

EOF