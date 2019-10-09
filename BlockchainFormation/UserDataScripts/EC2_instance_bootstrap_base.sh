#!/bin/bash -xe
exec > >(tee /var/log/user_data.log|logger -t user-data -s 2>/dev/console) 2>&1
  # Settings -> enable tracing for commands
  set -x

  # hosts file fix for localhost naming issue with sudo commands on ubuntu 18
  #127.0.0.1 localhost ip-10-6-57-68
  export hsname=$(cat /etc/hostname)
  bash -c 'echo 127.0.0.1 localhost $hsname >> /etc/hosts'

  # Do not delete the following lines, as it is needed to insert proxy; temp fix -> replace placeholder with string.replace in vm_handler.py
  # PROXY_PLACEHOLDER, DO NOT DELETE!


  #this is for going through some of the prompts for linux packages
  export DEBIAN_FRONTEND=noninteractive
  DEBIAN_FRONTEND=noninteractive apt-get update || apt-get update && apt-get upgrade -y || apt-get upgrade -y || echo "upgrading in base_bootstrap failed" >> /home/ubuntu/upgrade_fail.log
  apt-get dist-upgrade -y || apt-get dist-upgrade -y || echo "dist-upgrading in base_bootstrap failed" >> /home/ubuntu/upgrade_fail.log

  #Automatic Security Updates
  apt install unattended-upgrades || echo "Upgrading unattended upgrades in base_bootstrap failed" >> /home/ubuntu/upgrade_fail.log
  echo "APT::Periodic::Update-Package-Lists "1";
  APT::Periodic::Download-Upgradeable-Packages "1";
  APT::Periodic::AutocleanInterval "7";
  APT::Periodic::Unattended-Upgrade "1";" >> /etc/apt/apt.conf.d/20auto-upgrades

  # for monitoring of upload and download speed
  apt install -y ifstat || apt install -y ifstat || apt install -y ifstat
  # for monitoring disk i/o
  apt-get install sysstat -y || apt-get install sysstat -y || apt-get install sysstat -y


  # Time sync needed, careful we have to use chrony with 169.254.169.123 as ntp does not work behind proxy
  # https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/set-time.html
  sudo apt install chrony -y || sudo apt install chrony -y || sudo apt install chrony -y || sudo apt install chrony -y
  sudo sed -i '1s/^/server 169.254.169.123 prefer iburst minpoll 4 maxpoll 4\n/' /etc/chrony/chrony.conf
  sudo /etc/init.d/chrony restart
  chronyc sources -v || chronyc sources -v || chronyc sources -v

  #THIS ONLY WORKS IF THE UNMOUNTED DISK IS THE BIGGEST DISK ON VM
  UNMOUNTED=`lsblk --noheadings --raw -o NAME,MOUNTPOINT,SIZE | sort -u -h -k 2 | awk '{print $4 " " $1}'  | tail -n 1`
  #remove whitespace
  UNMOUNTED=`(echo -e "${UNMOUNTED}" | tr -d '[:space:]')`
  echo $UNMOUNTED
  #mounting disk
  mkdir /data
  mkfs -t ext4 /dev/$UNMOUNTED
  mount /dev/$UNMOUNTED /data
  DISKUUID=`sudo file -s /dev/$UNMOUNTED | awk '{print $8}'`
  bash -c  "echo '$DISKUUID       /data   ext4    defaults,nofail        0       2' >> /etc/fstab"

  bash -c  "sudo chown -R ubuntu:ubuntu /data"

  # switch to normal user
  cat << EOF | su ubuntu
  cd ~

  #echo "Initial Script finished, Starting more advanced installs now"

  #add users with bash shell



