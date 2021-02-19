#  Copyright 2021 ChainLab
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

   
  # =======  Create success indicator at end of this script ========== 
  touch /var/log/user_data_success.log 