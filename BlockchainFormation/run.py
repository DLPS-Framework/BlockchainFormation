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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KINDs, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import argparse
import json
import logging.config
import os
import sys

from utils.utils import yes_or_no
from Node_Handler import Node_Handler

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aws_cdk.cloud_assembly_schema
class ArgParser:

    def __init__(self):
        """Initialize an ArgParser object.
        The general structure of calls from the command line is:

        """

        self.parser = argparse.ArgumentParser(description='This script automizes setup for various blockchain networks on aws and calculates aws costs after finshing',
                                              usage='run.py start --config /home/config.json or run.py terminate --config /home/config.json')

        subparsers_start_terminate = self.parser.add_subparsers(help='start instances or terminate them')

        parser_start = subparsers_start_terminate.add_parser('start', help='startup')
        parser_termination = subparsers_start_terminate.add_parser('terminate', help='termination')

        parser_start.set_defaults(goal='start')
        parser_start.add_argument('--config', '-c', help='enter path to config file')

        parser_termination.add_argument('--config', '-c', help='enter path to config file')
        parser_termination.set_defaults(goal='termination')

    @staticmethod
    def storage_type(x):
        """Checks if the chosen storage is in a given range (Needs to be >1 else the mounting process of the UserData
        script fails)"""
        x = int(x)
        if x < 9 or x > 2048:
            raise argparse.ArgumentTypeError("Minimum storage is 9GB, maximum is 1024 GB")
        return x

    @staticmethod
    def load_config(namespace_dict):
        """
        Loads the config from a given JSON file
        :param namespace_dict: namespace dict containing the config file path
        :return: config dict
        """
        if namespace_dict['config'].endswith('.json'):
            try:
                with open(namespace_dict['config']) as json_file:
                    return json.load(json_file)
            except:
                logger.error("ERROR: Problem loading the given config file")
        else:
            logger.exception("Config file needs to be of type JSON")
            raise Exception("Config file needs to be of type JSON")


if __name__ == '__main__':
    argparser = ArgParser()
    namespace = argparser.parser.parse_args()

    logging.basicConfig(filename='logger.log', level=logging.DEBUG, format='%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')

    # BlockchainFormation: https://docs.python.org/3/howto/logging-cookbook.html
    # create logger with
    logger = logging.getLogger(__name__)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    if namespace.goal == 'start':

        # if no config file is given, a config file is created with the passed argpass commands
        if namespace.config is not None:
            logger.info("Given config file will be used")
            try:
                config = ArgParser.load_config(vars(namespace))
            except Exception as e:
                logger.info("Could not find or open the config file")
                raise Exception("Could not open config file")

        else:
            logger.info("No config file specified - exiting")
            raise Exception("Missing path to config file")

        node_handler = Node_Handler(config)
        try:
            node_handler.run_general_startup()
        except (Exception, KeyboardInterrupt) as e:
            logger.exception(e)
            if yes_or_no("Do you want to shut down the whole network?"):
                node_handler.run_general_shutdown()

        # node_handler.run_general_shutdown()

    elif namespace.goal == 'termination':
        config = ArgParser.load_config(vars(namespace))
        node_handler = Node_Handler(config)
        node_handler.run_general_shutdown()
