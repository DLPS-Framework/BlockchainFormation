#!/bin/bash -xe

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

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

  (cd ~/tezos; git checkout mainnet; opam init --bare -a)
  (cd ~/tezos; make build-deps || echo "Build_deps ended with error" >> /home/ubuntu/build_deps_fail.log)
  (cd ~/tezos; eval $(opam env) || echo "Eval ended with error" >> /home/ubuntu/eval_fail.log)
  (cd ~/tezos; make || echo "Make ended with error" >> make_fail.log)
  (cd ~/tezos; make || echo "Make failed again with error" >> make_fail.log)
  (cd ~/tezos; make || echo "Make failed third time with error" >> make_fail.log)
  export PATH=~/tezos:$PATH
  source ~/tezos/src/bin_client/bash-completion.sh
  export TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=Y

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF