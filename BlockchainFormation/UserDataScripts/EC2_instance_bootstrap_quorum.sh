#!/bin/bash -xe

  cd /data
  sudo chown -R ubuntu /data

  # Getting updates (and upgrades)
  sudo apt-get update
  sudo apt-get -y upgrade || echo "Upgrading in quorum_bootstrap failed" >> /home/ubuntu/upgrade_fail2.log

  # Installing go, java and make
  echo 'Y' | sudo apt-get install golang-go
  sudo apt install -y openjdk-8-jre-headless
  sudo apt-get install -y make

# Cloning repo and building Quorum binaries...
  git clone https://github.com/jpmorganchase/quorum.git
  # (cd /data/quorum && git checkout 99f7fd6733a93ee7619d1c740e0d4cd7643b6700)
  (cd /data/quorum && make all)

# Copying binaries to /usr/local/bin, which is in path!
  sudo cp /data/quorum/build/bin/geth /data/quorum/build/bin/bootnode /usr/local/bin

# Creating skeleton genesis block for RAFT consensus
  printf '{
  "alloc": {
    "0xsubstitute_address": {
      "balance": "10000000000000000000000000"
    }
  },
  "coinbase": "0x0000000000000000000000000000000000000000",
  "config": {
    "homesteadBlock": 0,
    "byzantiumBlock": 0,
    "constantinopleBlock": 0,
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
}\n' > /data/genesis_raw_raft.json

# Creating skeleton genesis block for IBFT consensus
  printf '{
  "alloc": {
    "0xsubstitute_address": {
      "balance": "10000000000000000000000000"
    }
  },
  "coinbase": "0x0000000000000000000000000000000000000000",
  "config": {
    "byzantiumBlock":  1,
    "constantinopleBlock":0,
    "chainId": 10,
    "eip150Block": 1,
    "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000",
    "eip155Block": 1,
    "eip158Block": 1,
    "isQuorum": true,
    "maxCodeSize" : 35,
    "istanbul": {
      "epoch": 30000,
      "policy": 0
    }
  },
  "extraData": "substitute_extra_data",
  "gasLimit": "0xE0000000",
  "difficulty": "0x1",
  "mixHash": "0x63746963616c2062797a616e74696e65206661756c7420746f6c6572616e6365",
  "nonce": "0x0",
  "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
  "timestamp": "0x00"
}\n' > /data/genesis_raw_istanbul.json


#extra data according to quorum ibft documentation
#"extraData": "0x0000000000000000000000000000000000000000000000000000000000000000f85ad5942aabbc1bb9bacef60a09764d1a1f4f04a47885c1b8410000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000c0",


  # Creating wallets and store the resulting address (needs some cosmetics)
  mkdir /data/nodes
  echo 'user' > /data/nodes/pwd
  # geth --password /data/nodes/pwd --datadir /data/nodes/new-node-1 account new > /data/nodes/address
  # sed -i -e 's/Address: //g' /data/nodes/address
  # sed -i -e 's/{//g' /data/nodes/address
  # sed -i -e 's/}//g' /data/nodes/address

  # Getting (already built, since building mit Libsodium & Maven did not work) tessera-app (jar) and generating tessera keys
  mkdir /data/tessera
  mkdir /data/qdata
  mkdir /data/qdata/tm

  # (cd /data/tessera && wget https://oss.sonatype.org/content/groups/public/com/jpmorgan/quorum/tessera-app/0.9.2/tessera-app-0.9.2-app.jar)
  (cd /data/tessera && wget https://oss.sonatype.org/service/local/repositories/releases/content/com/jpmorgan/quorum/tessera-app/0.10.0/tessera-app-0.10.0-app.jar)
  # java -jar /data/tessera/tessera-app-0.9.2-app.jar -keygen -filename /data/qdata/tm/tm < /dev/null
  java -jar /data/tessera/tessera-app-0.10.0-app.jar -keygen -filename /data/qdata/tm/tm < /dev/null

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
            "serverAddress": "unix:/data/qdata/tm/tm.ipc",
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
}' >> /data/config_raw.json

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF