#!/bin/bash -xe

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  sudo apt install -y jq

  sudo apt install -y rsync git m4 build-essential patch unzip bubblewrap wget pkg-config libgmp-dev libev-dev libhidapi-dev which
  wget https://github.com/ocaml/opam/releases/download/2.0.3/opam-2.0.3-x86_64-linux
  sudo cp opam-2.0.3-x86_64-linux /usr/local/bin/opam
  sudo chmod a+x /usr/local/bin/opam
  git clone https://gitlab.com/tezos/tezos.git
  cd tezos
  git checkout mainnet # or babylonnet or zeronet
  opam init --bare
  make build-deps
  eval $(opam env)
  make
  export PATH=~/tezos:$PATH
  source ./src/bin_client/bash-completion.sh
  export TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=Y

  #FROM ubuntu:18.04
  #RUN apt-get update -y
  #RUN apt-get install -y rsync git m4 build-essential patch unzip bubblewrap wget pkg-config libgmp-dev libev-dev libhidapi-dev libsodium-dev libcurl4-gnutls-dev ocaml
  #RUN apt-get install -y libgmp-dev m4 perl
  #RUN wget https://github.com/ocaml/opam/releases/download/2.0.3/opam-2.0.3-x86_64-linux
  #RUN cp opam-2.0.3-x86_64-linux /usr/local/bin/opam
  #RUN chmod a+x /usr/local/bin/opam
  #RUN git clone https://github.com/ocaml/dune.git
  #WORKDIR /dune/
  #RUN make release
  #RUN make install
  #WORKDIR /
  #RUN git clone https://gitlab.com/tezos/tezos.git
  #WORKDIR /tezos/
  #RUN git checkout alphanet
  #RUN opam init --bare --disable-sandboxing
  #RUN eval $(opam env)
  #RUN make build-deps
  #RUN eval $(opam env)
  #RUN opam update && opam upgrade -y
  #RUN opam config exec make
  #RUN export PATH=/tezos:$PATH
  ## RUN source ./src/bin_client/bash-completion.sh
  #RUN export TEZOS_CLIENT_UNSAFE_DISABLE_DISCLAIMER=Y
  #COPY ./start-tezos-sandbox.sh .
  #ENTRYPOINT ["./start-tezos-sandbox.sh"]

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF