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
#
  sudo mkdir /home/ubuntu/openethereum && cd /home/ubuntu/openethereum
  sudo wget https://github.com/openethereum/openethereum/releases/download/v3.2.0/openethereum-linux-v3.2.0.zip
  echo "After OpenEthereum download"

  sudo apt-get update
  sudo apt-get install unzip
  echo "After Unzip installation"

  sudo unzip openethereum*.zip
  sudo chmod +x openethereum
  echo "After OpenEthereum unzipping"

  cat > /home/ubuntu/openethereum/eth1.service << EOF
[Unit]
Description     = openethereum eth1 service
Wants           = network-online.target
After           = network-online.target

[Service]
User            = ubuntu
WorkingDirectory= /home/ubuntu/openethereum
ExecStart       = /home/ubuntu/openethereum/openethereum --config /data/parityNetwork/node.toml
Restart         = on-failure

[Install]
WantedBy	= multi-user.target
EOF
  echo "After OpenEthereum initialization"

  sudo mv /home/ubuntu/openethereum/eth1.service /etc/systemd/system/eth1.service
  sudo chmod 644 /etc/systemd/system/eth1.service
  echo "After eth1.service permissions"

  sudo systemctl daemon-reload
  sudo systemctl enable eth1
  sudo systemctl start eth1.service
  echo "Started!"

  sudo touch /var/log/user_data_success.log

#  sudo journalctl -u eth1 -f

