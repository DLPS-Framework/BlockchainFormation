 
  #only contains stuff needed for geth, base installation are in base shell script 
  # ======== Install Ethereum Geth ========

EOF

  sudo su
 
  bash -c  "sudo -E apt-get install --reinstall ca-certificates" || bash -c  "sudo -E apt-get install --reinstall ca-certificates" 
  bash -c  "sudo -E apt-get install software-properties-common" || bash -c  "sudo -E apt-get install software-properties-common" 
  #Added || to commands where proxy fails sometimes -> Fixes the problem so far 
  bash -c  "sudo -E add-apt-repository -y ppa:ethereum/ethereum" || bash -c  "sudo -E add-apt-repository -y ppa:ethereum/ethereum" || bash -c  "sudo -E add-apt-repository -y ppa:ethereum/ethereum" 
  bash -c  "sudo -E apt-get update" 
  bash -c  "sudo -E apt-get install ethereum -y" || bash -c  "sudo -E apt-get install ethereum -y" || bash -c  "sudo -E apt-get install ethereum -y" 
   
 
   
  # ======== Geth Network Setup ======== (https://atc.bmwgroup.net/confluence/display/BLOCHATEAM/Ethereum+%28Geth%29+Set+Up) 
  cd /data 
  mkdir gethNetwork 
  cd gethNetwork 
  mkdir node 
  PWD="password" 
  echo $PWD > password.txt 
  ACC=$( geth --datadir node/ account new --password password.txt ) 
  #FORMATTED_ACC_ID=$(echo $ACC|cut -d "{" -f2 | cut -d "}" -f1 ) 
  #Geth 1.9.0 changed the format of account creation 
  re="(.*--.*--)([[:alnum:]]+)([[:space:]])" 
  if [[ $ACC =~ $re ]]; then echo ${BASH_REMATCH[2]}; fi 
  FORMATTED_ACC_ID=${BASH_REMATCH[2]} 
  echo $FORMATTED_ACC_ID > account.txt 
  echo $FORMATTED_ACC_ID 
 
  cp -vr /data/gethNetwork/node/keystore/ /data 
  chown -R ubuntu /data/keystore/ 
  #DO NOT DO THIS IN REAL NETWORKS FOR SECURITY REASONS 
  chown -R ubuntu /data/gethNetwork/node/keystore/ 
  chown -R ubuntu /data/gethNetwork 
  chown -R ubuntu /etc/systemd/system/ 
   
  #Geth service setup 
  #https://github.com/bas-vk/config/blob/master/geth-systemd-service.md 
  #https://gist.github.com/xiaoping378/4eabb1915ec2b64a06e5b7d996bb8214 
  #--unlock $FORMATTED_ACC_ID 
  #--unlock $FORMATTED_ACC_ID --password /data/gethNetwork/password.txt --mine 
  IP=$( hostname -I ) 
  #bash -c  "sudo printf '%s\n' '[Unit]' 'Description=Ethereum go client' '[Service]' 'Type=simple' 'ExecStart=/usr/bin/geth --datadir /data/gethNetwork/node/ --networkid 11 --verbosity 3 --port 30310 --rpc --rpcaddr 0.0.0.0  --rpcapi db,clique,miner,eth,net,web3,personal,web3,admin,txpool --nat=extip:$IP  --syncmode full --mine ' 'StandardOutput=file:/var/log/geth.log' '[Install]' 'WantedBy=default.target' > /etc/systemd/system/geth.service" 
  #systemctl --user enable geth.service 
   
  #add log rotate 
   
  # ======= DOCKER Configs ========== 
 
  #bash -c "wget https://download.docker.com/linux/ubuntu/gpg" 
  #bash -c "sudo apt-key add gpg" 
  ##sudo add-apt-repository  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" 
  ##bash -c "apt update" 
  #add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable" 
  #apt update 
 
  #apt-get install docker-ce -y 
 
  ##sudo apt-get install docker-ce docker-ce-cli containerd.io 
 
  #mkdir /etc/systemd/system/docker.service.d 
  #touch /etc/systemd/system/docker.service.d/no_proxy.conf 
  #touch /etc/systemd/system/docker.service.d/http_proxy.conf 
  #touch /etc/systemd/system/docker.service.d/https_proxy.conf 
 
  #bash -c "printf '[Service]\nEnvironment=\"no_proxy=%s$NO_PROXY\"' >> /etc/systemd/system/docker.service.d/no_proxy.conf" 
  #bash -c "printf '[Service]\nEnvironment=\"http_proxy=%s$HTTP_PROXY\"' >> /etc/systemd/system/docker.service.d/http_proxy.conf" 
  #bash -c "printf '[Service]\nEnvironment=\"https_proxy=%s$HTTP_PROXY\"' >> /etc/systemd/system/docker.service.d/https_proxy.conf" 
 
  #systemctl daemon-reload 
  #service docker restart 
 
  apt install chrony -y || apt install chrony -y || apt install chrony -y 
  echo 'server 169.254.169.123 prefer iburst' >> /etc/chrony/chrony.conf 
  /etc/init.d/chrony restart 
   
  # =======  Create success indicator at end of this script ========== 
  touch /var/log/user_data_success.log 