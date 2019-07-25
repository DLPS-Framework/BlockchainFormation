#!/bin/bash -xe

  # Getting updates and upgrades
  sudo apt-get update
  sudo apt-get -y upgrade

  # Getting curl
  sudo apt install curl

  # Installing docker
  sudo apt install -y docker.io docker-compose
  # sudo docker run hello-world

  # Eventually user permissions need to be adjusted... rebooting required!
  sudo usermod -a -G docker ubuntu

  # Setting up go
  # echo 'Y' | sudo apt-get install golang-go
  wget -c https://dl.google.com/go/go1.12.7.linux-amd64.tar.gz
  sudo tar -xvzf go1.12.7.linux-amd64.tar.gz -C /usr/local
  rm go1.12.7.linux-amd64.tar.gz

  # Cloning hyperledger fabric + docker images
  curl -sSL http://bit.ly/2ysbOFE | sudo bash -s 1.4.1

  # Cloning github repository with helping material for Multi-Host-Network
  git clone https://github.com/wahabjawed/Build-Multi-Host-Network-Hyperledger.git
  sudo mv Build-Multi-Host-Network-Hyperledger fabric-samples

  # Putting fabric bins to path
  echo "export PATH=$PATH:/usr/local/go/bin:/home/ubuntu/fabric-samples/bin" >> /home/ubuntu/.profile
  # echo "export PATH=$PATH:/usr/local/go/bin:/home/ubuntu/fabric-samples/bin" | sudo tee -a /etc/profile > /dev/null
  source ~/.profile

  # Changing permissions for fabric-samples repository
  sudo chown --recursive ubuntu:ubuntu ~/fabric-samples/

# =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF