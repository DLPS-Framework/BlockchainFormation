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


import os


def ethermint_shutdown(config, logger, ssh_clients, scp_clients):
    """
    runs the ethermint specific shutdown operations (e.g. pulling the associated logs from the VMs)
    :return:
    """

    pass


def ethermint_startup(config, logger, ssh_clients, scp_clients):
    """
    Runs the ethermint specific startup script
    :return:
    """

    dir_name = os.path.dirname(os.path.realpath(__file__))


def ethermint_restart(config, logger, ssh_clients, scp_clients):
    """
    Runs the ethermint specific restart script
    :return:
    """

    pass
