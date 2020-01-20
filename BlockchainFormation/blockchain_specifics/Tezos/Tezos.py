#  Copyright 2019  ChainLab
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



import os
import time
import numpy as np
from BlockchainFormation.utils.utils import *

import hashlib


def tezos_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the tezos specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    pass


def tezos_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the geth specific startup script
    :return:
    """

    pass
