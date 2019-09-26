#  Copyright 2019 BMW Group
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

import logging
import json
import random
import string
from BlockchainFormation.utils.utils import *
#TODO How to accurately calculate load balancer costs


class LBHandler:
    """Class for handling aws application load balancer
    """

    def __init__(self, config, session):
        """
        Constructor
        :param config: config containing all info for creating LB
        :param session: boto3 session
        """

        self.config = config

        self.session = session
        if not self.logger.handlers:
            self.logger = logging.getLogger(__name__)
            ch = logging.StreamHandler()
            ch.setLevel(logging.DEBUG)
            # create formatter and add it to the handlers
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        self.lb_client = self.session.client('elbv2', region_name=self.config['aws_region'])

    def creation_routine(self):
        """creates lb, target group and add VMs as targets
        CreateLB -> Create TargetGroup -> create listeners -> create targets  -> route53 DNS record (-> Kill LB/TargetGroup)"""
        try:
            self.create_lb()
            # Wait until LB is ready
            self.logger.info("Waiting for the Load Balancer to be available")
            waiter = self.lb_client.get_waiter('load_balancer_available')
            waiter.wait(LoadBalancerArns=[self.config['load_balancer_settings']['LoadBalancerArn']])
            self.create_target_group()
            self.create_listener()
            self.register_targets()
            self.logger.info("Waiting for the targets to be in service")
            waiter = self.lb_client.get_waiter('target_in_service')
            waiter.wait(TargetGroupArn=self.config['load_balancer_settings']['TargetGroupArn'])
            self.create_dns_mapping()
        except Exception:
            raise Exception
        finally:
            with open(f"{self.config['exp_dir']}/config.json", 'w') as outfile:
                json.dump(self.config, outfile, indent=4, default=datetimeconverter)


    def create_lb(self):
        """
        Creates the Load Balancer itself
        :return:
        """

        #TODO make it work for public (Scheme='internet-facing')
        #[Application Load Balancers] You must specify subnets from at least two Availability Zones.
        # You cannot specify Elastic IP addresses for your subnets.
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_load_balancer
        self.logger.info("Creating load balancer now")
        lb_response = self.lb_client.create_load_balancer(
            Name=f"LB-{self.config['blockchain_type']}-{self.config['timestamp']}",
            Subnets=self.config['load_balancer_settings']['lb_subnet_ids'],
            SecurityGroups=self.config['load_balancer_settings']['lb_security_group_ids'],
            Scheme='internal',
            Tags=[
                {
                    'Key': 'Creator',
                    'Value': self.config['tag_name']
                },
                {
                    'Key': 'Name',
                    'Value': self.config['tag_name']
                },
            ],
            Type='application',
            IpAddressType='ipv4'
        )
        self.config['load_balancer_settings']['LoadBalancerArn'] = lb_response['LoadBalancers'][0]['LoadBalancerArn']
        self.config['load_balancer_settings']['DNSName'] = lb_response['LoadBalancers'][0]['DNSName']

        self.config['load_balancer_settings']['CanonicalHostedZoneId'] = lb_response['LoadBalancers'][0]['CanonicalHostedZoneId']

        self.logger.info(f"DNSName: {self.config['load_balancer_settings']['DNSName']}")
        self.logger.info(f"LoadBalancerArn: {self.config['load_balancer_settings']['LoadBalancerArn']}")



    def create_target_group(self):
        """
        Creates Target Group
        :return:
        """
        self.logger.info("Creating target group now")
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_target_group
        tg_response = self.lb_client.create_target_group(
            Name=f"TG-{self.config['blockchain_type']}-{self.config['timestamp']}",
            Protocol='HTTP',
            Port=self.config['load_balancer_settings']['lb_port'],
            VpcId=self.config['vpc_ids'][0],
            HealthCheckProtocol='HTTP',
            #HealthCheckPort=str(self.config['load_balancer_settings']['lb_port']),
            HealthCheckEnabled=True,
            HealthCheckPath='/api/health' if self.config['blockchain_type'] == 'parity' else '/',
            #HealthCheckIntervalSeconds=123,
            #HealthCheckTimeoutSeconds=123,
            #HealthyThresholdCount=123,
            #UnhealthyThresholdCount=123,
            Matcher={
                'HttpCode': '200'
            },
            TargetType='instance'

        )

        self.config['load_balancer_settings']['TargetGroupArn'] = tg_response['TargetGroups'][0]['TargetGroupArn']

        self.logger.info(f"TargetGroupArn: {self.config['load_balancer_settings']['TargetGroupArn']}")

    def create_listener(self):
        """
        Creates listener
        :return:
        """
        self.logger.info("Creating listener now")
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.create_listener
        l_response = self.lb_client.create_listener(
            LoadBalancerArn=self.config['load_balancer_settings']['LoadBalancerArn'],
            Protocol='HTTP',
            Port=self.config['load_balancer_settings']['lb_port'],
            DefaultActions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': self.config['load_balancer_settings']['TargetGroupArn'],
                    #'Order': 123,
                },
            ]
        )

        self.config['load_balancer_settings']['ListenerArn'] = l_response['Listeners'][0]['ListenerArn']

        self.logger.info(f"ListenerArn: {self.config['load_balancer_settings']['ListenerArn']}")

    def register_targets(self):
        """Register target for target group"""
        self.logger.info("Registering targets now")
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.register_targets
        rt_response = self.lb_client.register_targets(
            TargetGroupArn=self.config['load_balancer_settings']['TargetGroupArn'],
            Targets=[{'Id': id, 'Port': self.config['load_balancer_settings']['lb_port']} for id in self.config['instance_ids']]
        )

        #self.logger.debug(rt_response)

    def create_dns_mapping(self):
        """Map LB DNS name to route 53 dns record"""
        self.logger.info("Trying to create route53 record now")
        route53_client = self.session.client('route53', region_name=self.config['aws_region'])
        #TODO: Make dns name work for multiple profiles, not just experimental

        route53_dns_name = self.config['blockchain_type'] + "exp" + random.choice(string.ascii_letters).lower() + random.choice(string.ascii_letters).lower() +".blockchainlab.eu-central-1.aws.cloud.bmw."
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/route53.html#Route53.Client.change_resource_record_sets
        response = route53_client.change_resource_record_sets(
            HostedZoneId=self.config['load_balancer_settings']['lb_hosted_zone_id'],
            ChangeBatch={
                'Comment': "Create DNS record for load balancer of " + self.config['blockchain_type'] + " experiment",
                'Changes': [
                    {
                        'Action': 'CREATE',
                        'ResourceRecordSet': {
                            'Name': route53_dns_name , #random number to avoid the same dns names (better idea someone?)
                            'Type':  'A',
                            # 'ResourceRecords': [
                            #     {
                            #         'Value': 'string'
                            #     },
                            # ],
                            'AliasTarget': {
                                'HostedZoneId': self.config['load_balancer_settings']['CanonicalHostedZoneId'],
                                'DNSName': "dualstack."+self.config['load_balancer_settings']['DNSName'],
                                'EvaluateTargetHealth': False
                            },
                        }
                    },
                ]
            }
        )

        self.config['load_balancer_settings']['route53_dns'] = route53_dns_name
        self.logger.info(f"Route53 dns address which you can hit with web3 etc.: {self.config['load_balancer_settings']['route53_dns']}")

    def delete_dns_mapping(self):
        """delete route 53 record"""

        route53_client = self.session.client('route53', region_name=self.config['aws_region'])

        #hosted_zone_id: zone id for creating new route 53 record
        #CanonicalHostedZoneId: zone id of created load balancer

        response = route53_client.change_resource_record_sets(
            HostedZoneId=self.config['load_balancer_settings']['lb_hosted_zone_id'],
            ChangeBatch={
                'Comment': 'string',
                'Changes': [
                    {
                        'Action': 'DELETE',
                        'ResourceRecordSet': {
                            'Name': self.config['load_balancer_settings']['route53_dns'], #random number to avoid the same dns names (better idea someone?)
                            'Type':  'A',
                            'AliasTarget': {
                                'HostedZoneId': self.config['load_balancer_settings']['CanonicalHostedZoneId'],
                                'DNSName': "dualstack." + self.config['load_balancer_settings']['DNSName'],
                                'EvaluateTargetHealth': False
                            },
                        }
                    },
                ]
            }
        )
    def shutdown_lb(self):
        """Shutdown load balancer and target group"""

        self.logger.info("Load Balancer costs are not calculated at the moment!!!")
        self.logger.info("Shutdown listener now")
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.delete_listener
        response = self.lb_client.delete_listener(
             ListenerArn=self.config['load_balancer_settings']['ListenerArn']
         )


        self.logger.info("Shutdown target group")
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.delete_target_group
        dtg_response = self.lb_client.delete_target_group(
            TargetGroupArn=self.config['load_balancer_settings']['TargetGroupArn']
        )

        self.logger.info("Shutdown load balancer now")
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html#ElasticLoadBalancingv2.Client.delete_load_balancer
        dlb_response = self.lb_client.delete_load_balancer(
            LoadBalancerArn=self.config['load_balancer_settings']['LoadBalancerArn']
        )

        self.logger.info("Deleting route53 record now")
        self.delete_dns_mapping()


