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
EOF

  sudo su
  #only contains stuff needed for parity, base installation are in base shell script
  # ======== Install Ethereum Parity ========
  # try http for get parity instead of https
  bash -c  "bash <(curl http://get.parity.io -L) -r stable" || bash -c  "bash <(curl http://get.parity.io -L) -r stable" || bash -c  "bash <(curl https://get.parity.io -L) -r stable"  || bash -c  "bash <(curl https://get.parity.io -L) -r stable"

  # ======== Parity Network Setup ======== (https://wiki.parity.io/Demo-PoA-tutorial)
  cd /data
  sudo mkdir parityNetwork
  cd parityNetwork
  PWD="password"
  sudo bash -c "echo $PWD > password.txt"
  sudo chown -R ubuntu /data/parityNetwork/
  sudo chown -R ubuntu /data
  sudo chown -R ubuntu /etc/systemd/system/

  #Parity Service
  bash -c  "sudo printf '%s\n' '[Unit]' 'Description=Parity Ethereum client' '[Service]' 'Type=simple' 'ExecStart=/usr/bin/parity --config /data/parityNetwork/node.toml ' 'StandardOutput=file:/var/log/parity.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/parity.service"

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log





