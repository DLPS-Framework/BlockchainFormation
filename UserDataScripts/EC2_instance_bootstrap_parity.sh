
  #only contains stuff needed for geth, base installation are in base shell script
  # ======== Install Ethereum Parity ========
  # try http for get parity instead of https
  bash -c  "bash <(curl http://get.parity.io -L) -r stable" || bash -c  "bash <(curl http://get.parity.io -L) -r stable" || bash -c  "bash <(curl https://get.parity.io -L) -r stable"  || bash -c  "bash <(curl https://get.parity.io -L) -r stable"
  #bash -c  "bash <(wget -O - http://get.parity.io) -r stable" || bash -c  "bash <(wget -O - http://get.parity.io) -r stable"



  # ======== Parity Network Setup ======== (https://wiki.parity.io/Demo-PoA-tutorial)
  cd /data
  mkdir parityNetwork
  cd parityNetwork
  PWD="password"
  echo $PWD > password.txt
  chown -R ubuntu /data/parityNetwork/
  chown -R ubuntu /data
  chown -R ubuntu /etc/systemd/system/

  #Parity Service
  bash -c  "sudo printf '%s\n' '[Unit]' 'Description=Parity Ethereum client' '[Service]' 'Type=simple' 'ExecStart=/usr/bin/parity --config /data/parityNetwork/node.toml ' 'StandardOutput=file:/var/log/parity.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/parity.service"

  #add log rotate


  apt install chrony -y || apt install chrony -y || apt install chrony -y
  echo 'server 169.254.169.123 prefer iburst' >> /etc/chrony/chrony.conf
  /etc/init.d/chrony restart

  # =======  Create success indicator at end of this script ==========
  touch /var/log/user_data_success.log



