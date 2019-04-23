#!/bin/bash -xe
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
  echo "Hello from user-data!"
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

  echo "Init Script finished"
  
  #add users with bash shell


  # ======== Install Ethereum Geth ========

  add-apt-repository -y ppa:ethereum/ethereum
  apt-get update
  apt-get install ethereum -y

  # ======= DOCKER Configs ==========

  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
  add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
  apt update

  apt-get install docker-ce -y

  mkdir /etc/systemd/system/docker.service.d
  touch /etc/systemd/system/docker.service.d/no_proxy.conf
  touch /etc/systemd/system/docker.service.d/http_proxy.conf
  touch /etc/systemd/system/docker.service.d/https_proxy.conf

  bash -c "printf '[Service]\nEnvironment=\"no_proxy=%s$NO_PROXY\"' >> /etc/systemd/system/docker.service.d/no_proxy.conf"
  bash -c "printf '[Service]\nEnvironment=\"http_proxy=%s$HTTP_PROXY\"' >> /etc/systemd/system/docker.service.d/http_proxy.conf"
  bash -c "printf '[Service]\nEnvironment=\"https_proxy=%s$HTTP_PROXY\"' >> /etc/systemd/system/docker.service.d/https_proxy.conf"

  systemctl daemon-reload
  service docker restart


