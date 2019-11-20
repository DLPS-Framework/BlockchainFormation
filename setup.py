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


import setuptools
import os

ROOT = os.path.join(os.path.dirname(__file__), 'BlockchainFormation')

#TODO Add more required packages
requires = [
            'boto3>=1.9.134',
            'web3>=5.1.0',
            'paramiko>=2.6.0',
            'numpy>=1.17.3']

setuptools.setup(
    name="BlockchainFormation",
    version="0.0.1",
    author="ChainLab",
    #author_email="Philipp.P.Ross@bmw.de",
    description="Script which sets up multiple blockchains",
    #long_description=open('README.MD').read(),
    license="Apache License 2.0",
    install_requires=requires,
    #long_description=long_description,
    #long_description_content_type="text/markdown",
    include_package_data=True,
    packages=setuptools.find_packages(),
    #scripts=glob.glob("BlockchainFormation/UserDataScripts"), #/*.sh
    classifiers=[
        "Programming Language :: Python :: 3"
                ])
