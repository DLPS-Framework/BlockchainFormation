#!/bin/bash -xe
exec > >(tee /var/log/user_data.log|logger -t user-data -s 2>/dev/console) 2>&1
  # Settings -> enable tracing for commands
  set -x

  # hosts file fix for localhost naming issue with sudo commands on ubuntu 18
  #127.0.0.1 localhost ip-10-6-57-68
  export hsname=$(cat /etc/hostname)
  bash -c 'echo 127.0.0.1 localhost $hsname >> /etc/hosts'

  HTTP_PROXY=http://proxy.ccc.eu-central-1.aws.cloud.bmw:8080
  HTTPS_PROXY=https://proxy.ccc.eu-central-1.aws.cloud.bmw:8080
  NO_PROXY=localhost,127.0.0.1,.muc,.aws.cloud.bmw,.azure.cloud.bmw,.bmw.corp,.bmwgroup.net

  export http_proxy=$HTTP_PROXY
  export https_proxy=$HTTPS_PROXY
  export no_proxy=$NO_PROXY

  bash -c "echo http_proxy=$HTTP_PROXY >> /etc/environment"
  bash -c "echo https_proxy=$HTTPS_PROXY >> /etc/environment"
  bash -c "echo no_proxy=$NO_PROXY >> /etc/environment" 

  touch /etc/profile.d/environment_mods.sh
  bash -c "echo http_proxy=$HTTP_PROXY >> /etc/profile.d/environment_mods.sh"
  bash -c "echo https_proxy=$HTTPS_PROXY >> /etc/profile.d/environment_mods.sh"
  bash -c "echo no_proxy=$NO_PROXY >> /etc/profile.d/environment_mods.sh"   
  
  #test if sleeping works for the proxy problem
  sleep 5s
  
  #this is for going through some of the promts for linux packages
  export DEBIAN_FRONTEND=noninteractive
  DEBIAN_FRONTEND=noninteractive apt-get update && apt-get upgrade -y 
  apt-get dist-upgrade -y
  #apt-get install nginx -y

  #Automatic Security Updates
  apt install unattended-upgrades

  echo "APT::Periodic::Update-Package-Lists "1";
  APT::Periodic::Download-Upgradeable-Packages "1";
  APT::Periodic::AutocleanInterval "7";
  APT::Periodic::Unattended-Upgrade "1";" >> /etc/apt/apt.conf.d/20auto-upgrades


  #mounting disk

  mkdir /data
  mkfs -t ext4 /dev/xvdb
  mount /dev/xvdb /data
  DISKUUID=`sudo file -s /dev/xvdb | awk '{print $8}'`
  bash -c  "echo '$DISKUUID       /data   ext4    defaults,nofail        0       2' >> /etc/fstab"
  bash -c  "sudo chown -R ubuntu:ubuntu /data"

  #echo "Initial Script finished, Starting more advanced installs now"
  
  #add users with bash shell


  # ======== Install Ethereum Geth ========

  bash -c  "sudo -E apt-get install --reinstall ca-certificates"
  bash -c  "sudo -E apt-get install software-properties-common"
  bash -c  "sudo -E add-apt-repository -y ppa:ethereum/ethereum"
  bash -c  "sudo -E apt-get update"
  bash -c  "sudo -E apt-get install ethereum -y"
  

  
  # ======== Geth Network Setup ======== (https://atc.bmwgroup.net/confluence/display/BLOCHATEAM/Ethereum+%28Geth%29+Set+Up)
  cd /data
  mkdir gethNetwork
  cd gethNetwork
  mkdir node
  PWD="password"
  echo $PWD > password.txt
  ACC=$( geth --datadir node/ account new --password password.txt )
  FORMATTED_ACC_ID=$(echo $ACC|cut -d "{" -f2 | cut -d "}" -f1 )
  echo $FORMATTED_ACC_ID > account.txt
  echo $FORMATTED_ACC_ID
  
  #Geth service setup
  #https://github.com/bas-vk/config/blob/master/geth-systemd-service.md
  #https://gist.github.com/xiaoping378/4eabb1915ec2b64a06e5b7d996bb8214
  IP=$( hostname -I )
  bash -c  "sudo printf '%s\n' '[Unit]' 'Description=Ethereum go client' '[Service]' 'Type=simple' 'ExecStart=/usr/bin/geth --datadir /data/gethNetwork/node/ --networkid 11 --verbosity 3 --port 30310 --rpc --rpcaddr 0.0.0.0  --rpcapi db,clique,miner,eth,net,web3,personal,web3,admin,txpool --nat=extip:$IP  --unlock $FORMATTED_ACC_ID --password /data/gethNetwork/password.txt --mine ' 'StandardOutput=file:/var/log/geth.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/geth.service"
  #systemctl --user enable geth.service
  
  #add log rotate
  
  # ======= DOCKER Configs ==========

  #bash -c "wget https://download.docker.com/linux/ubuntu/gpg"
  #bash -c "sudo apt-key add gpg"
  ##sudo add-apt-repository  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
  ##bash -c "apt update"
  #add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
  #apt update

  #apt-get install docker-ce -y

  ##sudo apt-get install docker-ce docker-ce-cli containerd.io

  #mkdir /etc/systemd/system/docker.service.d
  #touch /etc/systemd/system/docker.service.d/no_proxy.conf
  #touch /etc/systemd/system/docker.service.d/http_proxy.conf
  #touch /etc/systemd/system/docker.service.d/https_proxy.conf

  #bash -c "printf '[Service]\nEnvironment=\"no_proxy=%s$NO_PROXY\"' >> /etc/systemd/system/docker.service.d/no_proxy.conf"
  #bash -c "printf '[Service]\nEnvironment=\"http_proxy=%s$HTTP_PROXY\"' >> /etc/systemd/system/docker.service.d/http_proxy.conf"
  #bash -c "printf '[Service]\nEnvironment=\"https_proxy=%s$HTTP_PROXY\"' >> /etc/systemd/system/docker.service.d/https_proxy.conf"

  #systemctl daemon-reload
  #service docker restart



