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


class Prometheus_Network:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the emtpy specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the prometheus specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        # channel = ssh_clients[0].get_transport().open_session()
        # channel.exec_command("cd /home/ubuntu/prometheus* && ./prometheus --config.file=prometheus.yml >> /home/ubuntu/prometheus.log")

    @staticmethod
    def restart(node_handler):
        """
        Runs the prometheus specific restart script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def attach_to_blockchain_conf(node_handler):
        """
        Attach prometheus settings to another config
        :param config:
        :param logger:
        :return:
        """

        config = node_handler.config
        logger = node_handler.logger

        try:
            with open(config["additional_settings"]["target_network_conf"]) as json_file:
                network_config_file = json.load(json_file)
        except:
            logger.error("ERROR: Problem loading the given config file")

        network_config_file["additional settings"] = {

            "ips": config["ips"],
            "exp_dir": config["exp_dir"],
            "aws_region": config["aws_region"],
        }

        try:
            network_config_file["additional settings"]['launch_times'] = config['launch_times'],
            network_config_file["additional settings"]['vpc_ids'] = config['vpc_ids']
            network_config_file["additional settings"]['instance_ids'] = config['instance_ids']
            network_config_file["additional settings"]['ips'] = config["ips"]
            network_config_file["additional settings"]['priv_ips'] = config['priv_ips']

        except Exception as e:
            logger.info("No vpc_ids and instance_ids available")

        logger.info("Attaching client config to parent network config now")
        logger.info(f"Target parent network: {config['additional_settings']['target_network_conf']}")
        if config['public_ip']:
            network_config_file["additional settings"]['pub_ips'] = config["pub_ips"]

        # write network config back
        with open(f"{config['additional_settings']['target_network_conf']}", 'w') as outfile:
            json.dump(network_config_file, outfile, default=datetimeconverter, indent=4)
