#!/bin/bash -xe

# Getting updates (and upgrades)
sudo apt-get update
sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

# ================== Install Amazon CloudFormation Scripts ===================
apt-get update
sleep 5s
apt-get update
sleep 5s
apt-get update || apt-get update
apt-get -y install python-pip
pip install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz
cp /usr/local/init/ubuntu/cfn-hup /etc/init.d/cfn-hup
chmod +x /etc/init.d/cfn-hup
update-rc.d cfn-hup defaults
service cfn-hup start

sleep 5s
# ================== Install Amazon CloudFormation Scripts ===================
#apt-get update || apt-get update || apt-get update || apt-get update
#apt-get -y install python-pip
#pip install https://s3.amazonaws.com/cloudformation-examples/aws-cfn-bootstrap-latest.tar.gz
#cp /usr/local/init/ubuntu/cfn-hup /etc/init.d/cfn-hup
#  - "#chmod +x /etc/init.d/cfn-hup ,"
#  - "#update-rc.d cfn-hup defaults  ,"
#  - "#service cfn-hup start ,"
#  - "sleep 5s,"

# Install policykit-1 for running applications as service
sudo apt install policykit-1 -y

# Install vim because no system should exist without it
sudo apt-get install vim -y

sudo apt-get update
sudo apt-get upgrade -y

# Fix 'locale' error for pip
sudo apt-get install locales -y
export LC_ALL=C

# Add sovrin repo to install libindy from (libindy-crypto is only available in xenial (16.04) repo)
#sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb bionic stable"
#sudo apt-get update
sudo apt-get install software-properties-common -y # Ubuntu 16.04
sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb xenial stable"
sudo apt-get update
sudo apt-get install -y libindy-crypto

# Python Tools
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt-get update
sudo apt-get install -y python3.6 python3-pip python3.6-dev
python3.6 -m pip install --upgrade setuptools

# Indy Aries Stuff
sudo apt-get install -y libindy
pip3 install --upgrade setuptools
sudo pip3 install python3-indy==1.11.0

## For libindy-crypto (for building with cargo, didn't work so far)
#sudo apt-get update && sudo apt-get install -y build-essential pkg-config cmake libssl-dev
#sudo apt-get install -y libindy-crypto=0.4.5

sudo mkdir /etc/indy /var/log/indy /var/lib/indy /var/lib/indy/backup /var/lib/indy/plugins
sudo chown -R ubuntu:ubuntu /var/log/indy/ /var/lib/indy/ /etc/indy/

# Install aries cloud agent (aka aca-py)
python3.6 -m pip install aries-cloudagent
#sudo pip3 install aries-cloudagent
sudo echo "export PATH="@@HOME/.local/bin:@@PATH"" >> ~/.bashrc
sudo sed -i -e 's/@@/$/g' ~/.bashrc
source ~/.bashrc # It should work now
source /home/ubuntu/.bashrc

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  sudo apt-get install -y make || sudo apt-get install -y make
  sudo apt install -y g++ || sudo apt install -y g++
  sudo apt install -y python2.7 python-pip || sudo apt install -y python2.7 python-pip

  sudo apt install -y postgresql postgresql-contrib

  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash || wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash
  . ~/.nvm/nvm.sh
  . ~/.profile
  . ~/.bashrc

  nvm install 8.16.0
  echo "export PATH=$PATH:/home/ubuntu/.nvm/versions/node/v8.16.0/bin" >> /home/ubuntu/.profile
  . ~/.profile
  . ~/.bashrc
  echo "node version: $(node -v)"
  echo "npm version: $(npm -v)"
  npm install -g typescript

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

  # Eventually user permissions need to be adjusted... rebooting required!
  sudo usermod -aG docker ubuntu
  newgrp docker
  # Testing whether docker runs without user permissions
  docker run hello-world

  # Install requirements for installing crypto stuff
  sudo apt-get install -y cmake autoconf libtool curl python3 pkg-config libssl-dev

  # Install Rust
  curl -sSf https://sh.rustup.rs | sh -s -- -y && source ~/.cargo/env

  # Download and build libsodium
  curl -fsSL https://github.com/jedisct1/libsodium/archive/1.0.18.tar.gz | tar -xz
  cd libsodium-1.0.18 && ./autogen.sh && ./configure --disable-dependency-tracking && make
  echo "export SODIUM_LIB_DIR=/usr/local/lib" >> /home/ubuntu/.profile && . ~/.profile
  echo "export LD_LIBRARY_PATH=/usr/local/lib" >> /home/ubuntu/.profile && . ~/.profile

  # Download and build ursa
  cd /home/ubuntu && git clone https://github.com/hyperledger/ursa.git
  cd /home/ubuntu/ursa/ && cargo build --release
  echo "export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/local/lib:/home/ubuntu/ursa/target/release" >> /home/ubuntu/.profile && . ~/.profile
  sudo cp /home/ubuntu/ursa/target/release/*.so /usr/lib

  # Get Indy stuff from Sovrin
  sudo add-apt-repository ppa:deadsnakes/ppa -y
	sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 68DB5E88 || echo "Adding keyserver failed" >> /home/ubuntu/upgrade_fail2.log
	sudo add-apt-repository "deb https://repo.sovrin.org/deb xenial master"
  sudo add-apt-repository "deb https://repo.sovrin.org/sdk/deb xenial stable"
  sudo add-apt-repository "deb http://us.archive.ubuntu.com/ubuntu xenial main universe"
	sudo apt-get update

  sudo apt-get install -y libsodium18
  sudo apt-get install -y python3.5 python3-pip python3.5-dev
	sudo apt-get install -y libindy libindy-crypto=0.4.5
	sudo pip3 install python3-indy==1.11.0 webhook_listener simplejson

	# Rust stuff
	curl https://sh.rustup.rs -sSf | sh -s -- -y
	source $HOME/.cargo/env

	git clone https://github.com/hyperledger/indy-sdk.git
	# cd ~/indy-sdk/libindy && cargo build
	# cd ~/indy-sdk/indy-cli && cargo build
	# cd ~/indy-sdk/experimental/plugins/postgres_storage && cargo build

  sudo mkdir /etc/indy /var/log/indy /var/lib/indy /var/lib/indy/backup /var/lib/indy/plugins
  sudo chown -R ubuntu:ubuntu /var/log/indy/ /var/lib/indy/ /etc/indy/

# =======  Create success indicator at end of this script ==========
sudo touch /var/log/user_data_success.log

EOF
