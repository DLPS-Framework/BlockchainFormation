#!/bin/bash -xe

  # Important: sawtooth seems to run only on Ubuntu 16.04.

  # Installing sawtooth stable build
  sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 8AA7AF1F1091A5FD
  sudo add-apt-repository 'deb [arch=amd64] http://repo.sawtooth.me/ubuntu/bumper/stable xenial universe'

  # For installing the nightly build
  # sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 44FC67F19B2466EA
  # sudo apt-add-repository 'deb [arch=amd64] http://repo.sawtooth.me/ubuntu/nightly xenial universe'

  # Installing all sawtooth repositories
  sudo apt-get update
  sudo apt-get install -y sawtooth
  sudo apt-get install -y sawtooth-devmode-engine-rust
  sudo apt-get install -y python3-sawtooth-poet-engine
  sudo apt-get install -y python3-sawtooth-identity


  # Generating keys
  sawtooth keygen
  sudo sawtooth keygen
  sudo sawadm keygen

  sudo -u sawtooth mkdir /home/sawtooth/temp

  # Generating skeleton config for the validator (toml-file!)
  printf '# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

#
# Sawtooth -- Validator Configuration
#

# This file should exist in the defined config directory and allows
# validators to be configured without the need for command line options.

# The following is a possible example.

# Bind is used to set the network and component endpoints. It should be a list
# of strings in the format "option:endpoint", where the options are currently
# network and component.
bind = [
  substitute_bind
  "component:tcp://127.0.0.1:4004",
  "consensus:tcp://127.0.0.1:5050"
]

# The type of peering approach the validator should take. Choices are static
# which only attempts to peer with candidates provided with the peers option,
# and dynamic which will do topology buildouts. If dynamic is provided,
# any static peers will be processed first, prior to the topology buildout
# starting.
peering = "static"

# Advertised network endpoint URL.
substitute_endpoint

# Uri(s) to connect to in order to initially connect to the validator network,
# in the format tcp://hostname:port. This is not needed in static peering mode
# and defaults to None. Replace host1 with the seeds hostname or IP address.
# substitute_seeds

# A list of peers to attempt to connect to in the format tcp://hostname:port.
# It defaults to None. Replace host1 with the peers hostname or IP address.
substitute_peers

# The type of scheduler to use. The choices are serial or parallel.
scheduler = "serial"

# A Curve ZMQ key pair are used to create a secured network based on side-band
# sharing of a single network key pair to all participating nodes.
# Note if the config file does not exist or these are not set, the network
# will default to being insecure.
network_public_key = "a2D#1XGI?qEKqF+^Pt{=usK5bS3ty$:Ws75iSN2x"
network_private_key  = "NcN<EwId)H57z8Rdq0@C[3u=-a!ar:o5AI{{ig^<"


# The minimum number of peers required before stopping peer search.
minimum_peer_connectivity = substitute_min_connectivity

# The maximum number of peers that will be accepted.
maximum_peer_connectivity = substitute_max_connectivity

# The host and port for Open TSDB database used for metrics
# opentsdb_url = ""

# The name of the database used for storing metrics
# opentsdb_db = ""

# opentsdb_username = ""

# opentsdb_password = ""

# The type of authorization that must be performed for the different type of
# roles on the network. The different supported authorization types are "trust"
# and "challenge". The default is "trust".

# [roles]
# network = "trust"

# Any off-chain transactor permission roles. The roles should match the roles
# stored in state for transactor permissioning. Due to the roles having . in the
# key, the key must be wrapped in quotes so toml can process it. The value
# should be the file name of a policy stored in the policy_dir.

# [permissions]
# transactor = "policy.example"
# "transactor.transaction_signer" = "policy.example"\n' > /home/ubuntu/validator.toml

  # Generating skeleton config file for the REST API (nothing to change yet)
  printf '#
# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

#
# Sawtooth -- REST API Configuration
#

# The port and host for the api to run on
  bind = ["substitute_local_private_ip:8008"]

# The url to connect to a running Validator
  connect = "tcp://localhost:4004"

# Seconds to wait for a validator response
#   timeout = 300

# The host and port for Open TSDB database used for metrics
# opentsdb_url = ""

# The name of the database used for storing metrics
# opentsdb_db = ""

# opentsdb_username = ""
# opentsdb_password = ""\n' > /home/ubuntu/rest_api.toml

  # Generating skeleton config file for the CLI (nothing to change yet)
  printf '#
# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

#
# Sawtooth -- CLI Configuration
#
# The REST API URL
  url = "http://localhost:8008"\n' > /home/ubuntu/cli.toml

  wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.34.0/install.sh | bash

  # =======  Create success indicator at end of this script ==========
  sudo touch /var/log/user_data_success.log

EOF