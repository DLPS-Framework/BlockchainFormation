#!/bin/bash -xe

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in quorum_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  # Installing go, java and make
  echo 'Y' | sudo apt-get install golang-go
  sudo apt install -y openjdk-8-jre-headless
  sudo apt-get install -y make

# Cloning repo and building Quorum binaries...
  git clone https://github.com/jpmorganchase/quorum.git
  (cd /home/ubuntu/quorum && make all)

# Copying binaries to /usr/local/bin, which is in path!
  sudo cp /home/ubuntu/quorum/build/bin/geth /home/ubuntu/quorum/build/bin/bootnode /usr/local/bin

  # Creating skeleton genesis block
  printf '{
  "alloc": {
    "0xsubstitute_first_address": {
      "balance": "10000000000000000000000000"
    },
    "0xsubstitute_second_address": {
      "balance": "10000000000000000000000000"
    }
  },
  "coinbase": "0x0000000000000000000000000000000000000000",
  "config": {
    "homesteadBlock": 0,
    "byzantiumBlock": 0,
    "constantinopleBlock":0,
    "chainId": 10,
    "eip150Block": 0,
    "eip155Block": 0,
    "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "eip158Block": 0,
    "isQuorum": true
  },
  "difficulty": "0x0",
  "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "gasLimit": "0xE0000000",
  "mixhash": "0x00000000000000000000000000000000000000647572616c65787365646c6578",
  "nonce": "0x0",
  "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "timestamp": "0x00"
}\n' > /home/ubuntu/genesis_raw.json

  # Creating wallets and store the resulting address (needs some cosmetics)
  mkdir /home/ubuntu/nodes
  echo 'user' > /home/ubuntu/nodes/pwd
  geth --password /home/ubuntu/nodes/pwd --datadir /home/ubuntu/nodes/new-node-1 account new > /home/ubuntu/nodes/address
  sed -i -e 's/Address: //g' /home/ubuntu/nodes/address
  sed -i -e 's/{//g' /home/ubuntu/nodes/address
  sed -i -e 's/}//g' /home/ubuntu/nodes/address

  # Getting (already built, since building mit Libsodium & Maven did not work) tessera-app (jar) and generating tessera keys
  mkdir /home/ubuntu/tessera
  mkdir /home/ubuntu/qdata
  mkdir /home/ubuntu/qdata/tm
  (cd /home/ubuntu/tessera && wget https://oss.sonatype.org/content/groups/public/com/jpmorgan/quorum/tessera-app/0.9.2/tessera-app-0.9.2-app.jar)
  java -jar /home/ubuntu/tessera/tessera-app-0.9.2-app.jar -keygen -filename /home/ubuntu/qdata/tm/tm < /dev/null

  # Preparing sceleton tessera config
  printf '{
    "useWhiteList": false,
    "jdbc": {
        "username": "sa",
        "password": "",
        "url": "jdbc:h2:.//qdata/tm/db;MODE=Oracle;TRACE_LEVEL_SYSTEM_OUT=0",
        "autoCreateTables": true
    },
    "serverConfigs": [
        {
            "app": "ThirdParty",
            "enabled": true,
            "serverAddress": "http://substitute_ip:9080",
            "communicationType": "REST"
        },
        {
            "app": "Q2T",
            "enabled": true,
            "serverAddress": "unix:/home/ubuntu/qdata/tm/tm.ipc",
            "communicationType": "REST"
        },
        {
            "app": "P2P",
            "enabled": true,
            "serverAddress": "http://substitute_ip:9000",
            "sslConfig": {
                "tls": "OFF",
                "generateKeyStoreIfNotExisted": true,
                "serverKeyStore": "/qdata/tm/server-keystore",
                "serverKeyStorePassword": "quorum",
                "serverTrustStore": "/qdata/tm/server-truststore",
                "serverTrustStorePassword": "quorum",
                "serverTrustMode": "TOFU",
                "knownClientsFile": "/qdata/tm/knownClients",
                "clientKeyStore": "/qdata/tm/client-keystore",
                "clientKeyStorePassword": "quorum",
                "clientTrustStore": "/qdata/tm/client-truststore",
                "clientTrustStorePassword": "quorum",
                "clientTrustMode": "TOFU",
                "knownServersFile": "/qdata/tm/knownServers"
            },
            "communicationType": "REST"
        }
    ],
    substitute_peers
    "keys": {
        "passwords": [],
        "keyData": [
            {
                "config": {
                    "type" : "unlocked",
                    "data" : {
                       "bytes" : "substitute_private_key"
                    }
                 },
                "publicKey": "substitute_public_key"
            }
        ]
    },
    "alwaysSendTo": []
}' >> /home/ubuntu/config_raw.json

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF