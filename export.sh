#!/bin/bash

  cd ~/PycharmProjects/BlockchainFormation/

  python setup.py sdist bdist_wheel

  ~/anaconda3/envs/ec2_automation/bin/pip install dist/BlockchainFormation-0.0.1.tar.gz