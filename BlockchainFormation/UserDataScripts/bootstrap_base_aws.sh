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


exec > >(tee /var/log/user_data.log|logger -t user-data -s 2>/dev/console) 2>&1
  # Settings -> enable tracing for commands
  set -xe

  # hosts file fix for localhost naming issue with sudo commands on ubuntu 18
  #127.0.0.1 localhost ip-10-6-57-68
  export hsname=$(cat /etc/hostname)
  bash -c 'echo 127.0.0.1 localhost $hsname >> /etc/hosts'

  # Do not delete the following lines, as it is needed to insert proxy; temp fix -> replace placeholder with string.replace in Node_Handler.py
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

  # Change Keep Alive Time of sshd
  sudo bash -c 'echo ClientAliveInterval 120 >> /etc/ssh/sshd_config'
  sudo bash -c 'echo ClientAliveCountMax 720 >> /etc/ssh/sshd_config'
  sudo bash -c 'echo MaxSessions 720 >> /etc/ssh/sshd_config'
  sudo service ssh restart

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

  # TODO Move this to ChainLab
  # Add a script which allows to set ip-specific delays later on
  printf '
#!/bin/bash

mode=$1
delay=$2
targets=$3

interface=ens5

function set_delays () {

    sudo tc qdisc del dev $interface root || echo "No existing interface $interface"
    sudo tc qdisc add dev $interface root handle 1: prio
    for i in ${targets[@]}; do
        sudo tc filter add dev $interface parent 1:0 protocol ip prio 1 u32 match ip dst $i flowid 2:1
        echo "set filter of $delay for $i"
    done
    sudo tc qdisc add dev $interface parent 1:1 handle 2: netem delay $delay

}

function remove_delays () {
    sudo tc qdisc del dev $interface root || echo "No existing interface $interface"
}

if [ "$mode" == "set" ]; then
    set_delays
else
    remove_delays
fi
' > /home/ubuntu/set_delays.sh

  chmod 777 /home/ubuntu/set_delays.sh


  # switch to normal user
#cat << EOF | su ubuntu
#  cd ~
#
#  echo "Initial Script finished, Starting more advanced installs now"
#
#  #add users with bash shell
#
#EOF