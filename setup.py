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

import setuptools
import glob


#with open("README.MD", "r") as fh:
 #   long_description = fh.read()
#print(setuptools.find_packages())

# source: https://github.com/pminkov/kubeutils

setuptools.setup(
    name="BlockchainFormation",
    version="0.0.1",
    author="BMW Blockchain Team",
    author_email="Philipp.P.Ross@bmw.de",
    description="Script which sets up multiple blockchains",
    license="Apache License 2.0",
    #long_description=long_description,
    #long_description_content_type="text/markdown",
    #url="https://atc.bmwgroup.net/bitbucket/projects/BLOCKCHAIN/repos/blockchainformation/",
    include_package_data=True,
    packages=setuptools.find_packages(),
    #scripts=glob.glob("BlockchainFormation/UserDataScripts"), #/*.sh
    classifiers=[
        "Programming Language :: Python :: 3"
    ],
)