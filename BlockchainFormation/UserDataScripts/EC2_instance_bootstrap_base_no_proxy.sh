#!/bin/bash -xe
exec > >(tee /var/log/user_data.log|logger -t user-data -s 2>/dev/console) 2>&1
  # Settings -> enable tracing for commands
  set -x



  # hosts file fix for localhost naming issue with sudo commands on ubuntu 18
  #127.0.0.1 localhost ip-10-6-57-68
  export hsname=$(cat /etc/hostname)
  bash -c 'echo 127.0.0.1 localhost $hsname >> /etc/hosts'

  #this is for going through some of the promts for linux packages
  export DEBIAN_FRONTEND=noninteractive
  DEBIAN_FRONTEND=noninteractive apt-get update || apt-get update && apt-get upgrade -y || apt-get upgrade -y
  apt-get dist-upgrade -y || apt-get dist-upgrade -y
  #apt-get install nginx -y

  #Automatic Security Updates
  apt install unattended-upgrades

  echo "APT::Periodic::Update-Package-Lists "1";
  APT::Periodic::Download-Upgradeable-Packages "1";
  APT::Periodic::AutocleanInterval "7";
  APT::Periodic::Unattended-Upgrade "1";" >> /etc/apt/apt.conf.d/20auto-upgrades


  UNMOUNTED=`lsblk --noheadings --raw -o NAME,MOUNTPOINT | awk '$1~/[[:digit:]]/ && $2 == ""'`
  echo $UNMOUNTED
  #mounting disk
  # On some instance types the disk has different name
  mkdir /data
  #mkfs -t ext4 /dev/xvdb || mkfs -t ext4 /dev/nvme0n1
  mkfs -t ext4 /dev/xvdb || yes N | mkfs -t ext4 /dev/nvme0n1 || yes N | mkfs -t ext4 /dev/nvme1n1
  mount /dev/xvdb /data || mount /dev/nvme0n1 /data || mount /dev/nvme1n1 /data

  #TEMP FIX
  DISKUUID=`sudo file -s /dev/xvdb | awk '{print $8}'`
  bash -c  "echo '$DISKUUID       /data   ext4    defaults,nofail        0       2' >> /etc/fstab"

  DISKUUID=`sudo file -s /dev/nvme0n1 | awk '{print $8}'`
  bash -c  "echo '$DISKUUID       /data   ext4    defaults,nofail        0       2' >> /etc/fstab"

  DISKUUID=`sudo file -s /dev/nvme1n1 | awk '{print $8}'`
  bash -c  "echo '$DISKUUID       /data   ext4    defaults,nofail        0       2' >> /etc/fstab"

  bash -c  "sudo chown -R ubuntu:ubuntu /data"

  # switch to normal user
  cat << EOF | su ubuntu
  cd ~

  #echo "Initial Script finished, Starting more advanced installs now"

  #add users with bash shell
