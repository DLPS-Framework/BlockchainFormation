import json
import datetime


def client_startup(config, logger, ssh_clients, scp_clients):
    """
    Startup for the blockchain client option
    :param config:
    :param logger:
    :param ssh_clients:
    :param scp_clients:
    :return:
    """

    if config["client_settings"]["target_network_conf"] is not None:
        # Attach client IPs to network conf
        attach_to_blockchain_conf(config, logger)



def datetimeconverter(o):
    """Converter to make datetime objects json dumpable"""
    if isinstance(o, datetime.datetime):
        return o.__str__()


def attach_to_blockchain_conf(config, logger):
    """
    Attach client settings to another config
    :param config:
    :param logger:
    :return:
    """
    try:
        with open(config["client_settings"]["target_network_conf"]) as json_file:
            network_config_file = json.load(json_file)
    except:
        logger.error("ERROR: Problem loading the given config file")

    # TODO: Make it possible to start the client script multiple times for the same parent experiment
    network_config_file["client settings"] = {

        "ips": config["ips"],
        "vpc_ids": config["vpc_ids"],
        "instance_ids": config["instance_ids"],
        "launch_times": config["launch_times"],
        "exp_dir": config["exp_dir"]

    }
    logger.info("Attaching client config to parent network config now")
    logger.info(f"Target parent network: {config['client_settings']['target_network_conf']}")
    if config['public_ip']:
        network_config_file["client settings"]['public_ips'] = 'public_ips'

    # write network config back
    with open(f"{config['client_settings']['target_network_conf']}", 'w') as outfile:
        json.dump(network_config_file, outfile, default=datetimeconverter, indent=4)