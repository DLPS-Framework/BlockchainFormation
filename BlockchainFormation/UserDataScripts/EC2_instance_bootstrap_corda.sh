#!/bin/bash -xe

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in indy_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  sudo apt install git
  git --version

  sudo apt-get install -y openjdk-8-jdk

  sudo apt-get update
  sudo apt install -y gradle 4.10
  sudo update-alternatives --config java
  # choose java 8 as default
  java -version

  (cd /data && git clone https://github.com/corda/samples)
  (cd /data/samples/cordapp-example && ./gradlew deployNodes)


  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF