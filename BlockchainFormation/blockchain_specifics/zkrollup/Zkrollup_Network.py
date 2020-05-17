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


class Zkrollup_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the Zkrollup specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the Zkrollup specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        dir_name = os.path.dirname(os.path.realpath(__file__))

        logger.info("Uploading the required setup files")
        scp_clients[0].put(f"{dir_name}/setup", "/home/ubuntu", recursive=True)

        logger.info("Installing required packages")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && npm install")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        logger.info("Compiling the circuit into r1cs - can take a few seconds to minutes")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && circom rollup.circom --r1cs && snarkjs info circuit.json && cp circuit.json circuit.r1cs")
        logger.info("\n".join(stdout.readlines()))
        logger.info(stderr.readlines())

        logger.info("Generating the trusted setup")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && snarkjs setup -r circuit.json")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        logger.info("Compiling the circuit into wasm - can take a few seconds to minutes")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && circom rollup.circom --wasm && cp circuit.json circuit.wasm")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        logger.info("Generating an input")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && node index.js")
        logger.info("\n".join(stdout.readlines()))
        logger.info(stderr.readlines())

        logger.info("Generating a witness from the input")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && snarkjs calculatewitness --wasm circuit.json --input input.json --witness witness.json")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        logger.info("Generating a proof from the input")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && snarkjs proof")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())

        logger.info("Verifying the proof")
        stdin, stdout, stderr = ssh_clients[0].exec_command(". ~/.profile && cd setup && node test.js")
        logger.info(stdout.readlines())
        logger.info(stderr.readlines())


    @staticmethod
    def restart(node_handler):
        """
        Runs the Zkrollup specific restart script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients
