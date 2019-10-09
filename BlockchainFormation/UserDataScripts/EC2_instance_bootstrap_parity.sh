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

  # Change open file limit to avoid Too many open files error
  #sudo bash -c 'echo 100000000 > /proc/sys/fs/file-max'
  #sudo bash -c 'fs.file-max = 100000000 >> /etc/sysctl.conf'
  #sudo sysctl -p

  #Parity Service
  bash -c  "sudo printf '%s\n' '[Unit]' 'Description=Parity Ethereum client' '[Service]' 'Type=simple' 'ExecStart=/usr/bin/parity --config /data/parityNetwork/node.toml ' 'StandardOutput=file:/var/log/parity.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/parity.service"

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log





