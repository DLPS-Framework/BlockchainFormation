#  Copyright 2019  Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
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

import re
import json
from pkg_resources import resource_filename
import logging
from BlockchainFormation.utils.utils import *


class AWSCostCalculator:
    """
    Class responsible for calculating the aws costs caused by one or more aws instances during their uptime,
     including attached ebs storage.
    """
    # TODO: Check if Calculation is correct (30 days vs. 31 days question)
    def __init__(self, session):

        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(threadName)s - %(name)s - %(levelname)s - %(message)s')
            # fh.setFormatter(formatter)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)
        
        self.pricing_client = session.client('pricing', region_name='us-east-1')

        self.session = session


    def calculate_uptime_costs(self, config):
        """
        Calculate uptime costs from launch to stopping of the VMs
        :param config:
        :return:
        """

        self.config = config
        ec2 = self.session.resource('ec2', region_name=self.config['aws_region'])
        self.ec2_instances = [ec2.Instance(instance_id) for instance_id in self.config['instance_ids']]

        launch_times = self.config['launch_times']

        stop_times = []
        self.logger.info("Waiting for all instances to reach stopped status")
        for i in self.ec2_instances:
            i.wait_until_stopped()
            stop_time = self._calculate_transition_time(i)
            stop_times.append(datetime.datetime.strptime(stop_time, '%Y-%m-%d %H:%M:%S %Z'))

        self.logger.info("All instances have now reached stopped status")
        self.logger.info("Launch Times:" + str(launch_times))
        self.logger.info("Stop Times:" + str([x.strftime('%Y-%m-%d %H:%M:%S') for x in stop_times]))

        if type(launch_times[0]) is str:
            time_differences = np.subtract(stop_times, [
                datetime.datetime.strptime(x, '%Y-%m-%d %H:%M:%S') for x in launch_times])
        else:
            time_differences = np.subtract(stop_times, [datetime.datetime.strptime(x.strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S') for x in launch_times])

        def diff_in_hours(x):
            return float(x.total_seconds() / 3600)

        time_diff_in_hours = list(map(diff_in_hours, time_differences))

        # self.logger.info(time_diff_in_hours)

        # dict for all storage 
        self.storage_dict = {
            'standard': 0,
            'gp2': 0,
            'io1': 0,
            'st1': 0,
            'sc1': 0
        }

        ec2 = self.session.resource('ec2', region_name=self.config['aws_region'])
        image = ec2.Image(self.config['image']['image_id'])
        root_storage_mapping = image.block_device_mappings

        self._extract_ebs_storage_from_blockdevicemapping(self.config['storage_settings'])
        self._extract_ebs_storage_from_blockdevicemapping(root_storage_mapping)
        #self.logger.info(self.storage_dict)
        # Use AWS Pricing API at eu-central-1
        # 'eu-central-1' not working -> Pricing the same ? 

        # Get current price for a given instance, region and os
        # make operation system not hardcoded
        instance_price_per_hour = float(self._get_instance_price(self._get_region_name(self.config['aws_region']), self.config['instance_type'], 'Linux'))

        # For example, let's say that you provision a 2000 GB volume for 12 hours (43,200 seconds) in a 30 day month.
        # In a region that charges $0.10 per GB-month, you would be charged $3.33 for the volume ($0.10 per GB-month
        # * 2000 GB * 43,200 seconds / (86,400 seconds/day * 30 day-month)).
        # source: https://aws.amazon.com/ebs/pricing/?nc1=h_ls
        # get price of used storage
        storage_price_per_hour = sum(
            [float(self._get_storage_price(self._get_region_name(self.config['aws_region']), volume_type)) * float(volume_size) / 30 / 24 for
             volume_type, volume_size in self.storage_dict.items()])

        self.logger.info("Instance cost per hour: " + str(np.round(instance_price_per_hour, 4)))
        self.logger.info("Storage cost per hour: " + str(np.round(storage_price_per_hour, 4)))

        # calculate price for each instance and then sum up the prices of all instances up to once total price
        total_instance_cost_until_stop = sum(map(lambda x: x * instance_price_per_hour, time_diff_in_hours))
        total_storage_cost_until_stop = sum(map(lambda x: x * storage_price_per_hour, time_diff_in_hours))

        self.logger.info(f"The total instance cost of {self.config['vm_count']} {self.config['instance_type']} instances running for averagely {np.round(np.mean(time_diff_in_hours),4)} hours was: {np.round(total_instance_cost_until_stop, 4)} USD.")
        self.logger.info(f"The total storage  cost of {self.config['vm_count']} {self.storage_dict} storage units running for averagely {np.round(np.mean(time_diff_in_hours),4)} hours was: {np.round(total_storage_cost_until_stop, 4)} USD.")
        total_cost_until_stop = total_instance_cost_until_stop + total_storage_cost_until_stop
        self.logger.info(f"Total Cost: {np.round(total_cost_until_stop, 4)} USD")

        aws_costs = {
            'instance_type': config['instance_type'],
            'vm_count': config['vm_count'],
            'storage_in_GB': self.storage_dict,
            'launch_times': launch_times,
            'stop_times': stop_times,
            'instance_price_per_hour': instance_price_per_hour,
            'storage_price_per_hour': storage_price_per_hour,
            'total_cost_until_stop': total_cost_until_stop,
            'currency': 'USD'

        }

        with open(f"{self.config['exp_dir']}/aws_costs.json", 'w') as outfile:
            json.dump(aws_costs, outfile, default=datetimeconverter)

    def _get_instance_price(self, region, instance, osys):
        """
        get instance price for given region, instance type and osys
        :param region:
        :param instance:
        :param osys:
        :return:
        """
        data = self.pricing_client.get_products(ServiceCode='AmazonEC2',
                                           Filters=[{"Field": "tenancy", "Value": "shared", "Type": "TERM_MATCH"},
                                                    {"Field": "operatingSystem", "Value": osys, "Type": "TERM_MATCH"},
                                                    {"Field": "preInstalledSw", "Value": "NA", "Type": "TERM_MATCH"},
                                                    {"Field": "instanceType", "Value": instance, "Type": "TERM_MATCH"},
                                                    {"Field": "location", "Value": region, "Type": "TERM_MATCH"}])

        od = json.loads(data['PriceList'][0])['terms']['OnDemand']
        id1 = list(od)[0]
        id2 = list(od[id1]['priceDimensions'])[0]
        return od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']

    def _get_storage_price(self, region, volume_type):
        """
        get storage price for given region and volume_type
        :param region: region
        :param volume_type: volume_type
        :return:
        """
        ebs_name_map = {
            'standard': 'Magnetic',
            'gp2': 'General Purpose',
            'io1': 'Provisioned IOPS',
            'st1': 'Throughput Optimized HDD',
            'sc1': 'Cold HDD'
        }
        data = self.pricing_client.get_products(ServiceCode='AmazonEC2',
                                           Filters=[
                                               {'Type': 'TERM_MATCH', 'Field': 'volumeType',
                                                'Value': ebs_name_map[volume_type]},
                                               {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region}])
        od = json.loads(data['PriceList'][0])['terms']['OnDemand']
        id1 = list(od)[0]
        id2 = list(od[id1]['priceDimensions'])[0]
        return od[id1]['priceDimensions'][id2]['pricePerUnit']['USD']

    def _get_region_name(self, region_code):
        """get region name for given region code"""
        default_region = 'EU (Frankfurt)'
        endpoint_file = resource_filename('botocore', 'data/endpoints.json')
        try:
            with open(endpoint_file, 'r') as f:
                data = json.load(f)
            return data['partitions'][0]['regions'][region_code]['description']
        except IOError:
            return default_region

    def _extract_ebs_storage_from_blockdevicemapping(self, b_d_mapping):
        """Extracts all ebs storage from a blockdevicemapping and stores them in storage_dict"""
        for device in b_d_mapping:
            if "Ebs" in device:
                self.storage_dict[device["Ebs"]["VolumeType"]] += device["Ebs"]["VolumeSize"]

    def _calculate_transition_time(self, instance, new_state="stopped"):
        """Calculate the  stop time of a given VM instance"""

        # get stop time for all stopped instances
        # https://stackoverflow.com/questions/41231630/checking-stop-time-of-ec2-instance-with-boto3
        client = self.session.client('ec2', region_name=self.config['aws_region'])
        rsp = client.describe_instances(InstanceIds=[instance.id])
        if rsp:
            status = rsp['Reservations'][0]['Instances'][0]
            if status['State']['Name'] == new_state:
                stopped_reason = status['StateTransitionReason']
                transition_time = re.findall('.*\((.*)\)', stopped_reason)[0]
                # print (f"Stop Time of {instance.id}:{stop_time}")

                return transition_time
