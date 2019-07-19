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