#!/bin/bash -xe

  sudo apt-get update
  sudo apt-get install upgrades

  sudo apt install -y openjdk-8-jre-headless

  (cd /data && git clone https://github.com/corda)

