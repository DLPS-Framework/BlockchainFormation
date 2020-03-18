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


import json
import os

from BlockchainFormation.utils.utils import *


class Tezos:

    @staticmethod
    def shutdown(node_handler):
        """
        runs the tezos specific shutdown operations (e.g. pulling the associated logs from the VMs)
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

    @staticmethod
    def startup(node_handler):
        """
        Runs the tezos specific startup script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients

        dir_name = os.path.dirname(os.path.realpath(__file__))

        config['node_indices'] = list(range(0, config['vm_count']))
        config['groups'] = [config['node_indices']]

        # Creating docker swarm
        logger.info("Preparing & starting docker swarm")

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm init")
        out = stdout.readlines()
        # for index, _ in enumerate(out):
        #     logger.debug(out[index].replace("\n", ""))

        # logger.debug("".join(stderr.readlines()))

        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker swarm join-token manager")
        out = stdout.readlines()
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))
        join_command = out[2].replace("    ", "").replace("\n", "")

        for index, _ in enumerate(config['priv_ips']):

            if index != 0:
                stdin, stdout, stderr = ssh_clients[index].exec_command("sudo " + join_command)
                out = stdout.readlines()
                # logger.debug(out)
                # logger.debug("".join(stderr.readlines()))

        config['join_command'] = "sudo " + join_command

        # Name of the swarm network
        my_net = "my-net"
        stdin, stdout, stderr = ssh_clients[0].exec_command(f"sudo docker network create --subnet 10.10.0.0/16 --attachable --driver overlay {my_net}")
        out = stdout.readlines()
        # logger.debug(out)
        # logger.debug("".join(stderr.readlines()))
        network = out[0].replace("\n", "")

        logger.info("Testing whether setup was successful")
        stdin, stdout, stderr = ssh_clients[0].exec_command("sudo docker node ls")
        out = stdout.readlines()
        for index, _ in enumerate(out):
            logger.debug(out[index].replace("\n", ""))

        logger.debug("".join(stderr.readlines()))
        if len(out) == len(config['priv_ips']) + 1:
            logger.info("Docker swarm started successfully")
        else:
            logger.info("Docker swarm setup was not successful")
            # sys.exit("Fatal error when performing docker swarm setup")

        config['private_keys'] = ['unencrypted:edsk2yx55QWfXKxZsYUyUDq99V3uvvvqSZjpsWAT5oeeWse4PLewGr', 'unencrypted:edsk37Kq8cUwpP3eUeZtt9Jd3Gx4r3i1f4xG17NNH4PgKAJ5nEWTCp', 'unencrypted:edsk4Et58xNeTKa1jsTBmzX5ciyyC2UGShuLZzbJQeFpwNVvnfPuM5',
                                  'unencrypted:edsk2jZt8VbGbdRYyNknATyu2VRB9HYDyL2DphjahjpVmeUd7nbCZx', 'unencrypted:edsk3e6Htfo1MZq9LfzopRQMPrxSxtgQQfxsbVykC8duJ4U4AknRM9', 'unencrypted:edsk4Eh8K6vuMLVmTNURkzqX3RgZpSnu1T8H8v9CE32zsfWMVK1Qcw',
                                  'unencrypted:edsk2gA4amiDKX1TfV4BfoT4TpdHW9DPXkaCd53p3MWzH3PNg82r3p', 'unencrypted:edsk31KQcM1zwJSCKqEct17knATCYLsskS6di7U2NtLeaVD3ZLHztk', 'unencrypted:edsk3g3FyGZVxkXrcxCY1dpwL7AB4RJgwpdKWeTiL6Gvph8zuSAUdY',
                                  'unencrypted:edsk48PqToB9YRMJJeaco4KNhxeRqBm5sMwv2FdmgTCLcCveRq2UXr', 'unencrypted:edsk2sMgojqz2b22V1AH9mEJpCYYjUox7aYcAMZxiFbwLYgPL3CjaG', 'unencrypted:edsk2nGDeSWpc8jm5bQyDeZ73pJAyjTTA7x5LWtQHvmauF9kJSnSpp',
                                  'unencrypted:edsk3BiYJMNsNcmxDPMop1YmF4xKoWQ7cieVvjc2n3MZ2BHQ2oehio', 'unencrypted:edsk3EmVr4t9cyj6ti42gXjhThqFw8YobpKiM7k9dK7BG8Gu3mh9P8', 'unencrypted:edsk3ie95yzDKeDUhem12L1tLuPLFVkWkkWrinFSqGA6igs1sbiNza',
                                  'unencrypted:edsk3uZCm7cKGrVnEWX531haikVPYvTDMqcvfbytebHnmVrCLUg86u', 'unencrypted:edsk2wmN1miKh4RmDQVJEuTnpJcopauwUpUc868zYtv1fgCTRbfkfc', 'unencrypted:edsk2msy66o8bcAYQrefUPpCUZWkXxCLFWnXVP1dmUmmAutEtC9gDT',
                                  'unencrypted:edsk3uHjispUs9VMB5RxSN933cbV3s3nd4aoWzeRtFtNWCRJjAaHR7', 'unencrypted:edsk3m5tLBjD4A3DHvGEeGMRL8Fhcd199mERL9jaGNn9JKZer98GPH', 'unencrypted:edsk3tA9uX7bbcFXKhqHZw8yLysL9PJc1TyUzrCGxaXHdhQw1vWmTr',
                                  'unencrypted:edsk3vMJAR6mTaRnhGNxW16NssJVhNkMeMnos3TQntuN2NuNYLQqXf', 'unencrypted:edsk3ycD7emCtyEqTNP5xf5cTdz8QWgYHzp91S8qnfWy4aiq1EDRA5', 'unencrypted:edsk4Ria1Cs43X2DxQn17xP9UBht6D5ZDyEQCAjENWw8P12BujjKAx',
                                  'unencrypted:edsk3Z4EBK3fpQmsfpHnSWnJXRL1gg26KkZ2Qx86bUWywn2CyZwE1p', 'unencrypted:edsk4F2i5YTmMmVCF8kxaHVdgnQtcfWaeWEWdr1UYiToAw1LmoAtP5', 'unencrypted:edsk3DHWjgVbxE6zAvoMFz7EciJq487meVQ7UQH2Mi3BBUrGGwBAqu',
                                  'unencrypted:edsk3tje6nKy3NGj7XdbxqP5qmEnBaW6ZaraKkwR4WjxHxxJymgUdb', 'unencrypted:edsk2pEwHowEdCxGvonjTY7KozWbuQyYhwtcKc9SvHjSL2gWe4T8Fq', 'unencrypted:edsk3SAwBxuJdYnsjdsmuNvqFQBvptkrnQ4jaqBFjz4QCx7D51FanC',
                                  'unencrypted:edsk3UZNMmq17S76ugZc35tkgr2gRoKx5xh66k28tUx9cnwj2Zc7wC', 'unencrypted:edsk3YJesWQt7y8364XYokaG1xYJU25knipSM7Uq7SKv14qGSNN9tX', 'unencrypted:edsk3LF8grWbWb5E13VeZhTnzQWUy3LsnH8js9KSPaTN36Z812A23n',
                                  'unencrypted:edsk3rfRAwP9F539beYgBU9xtZpkUhwGZMeNLUs8qxYeb8wXwBLUuP', 'unencrypted:edsk3cZKhZk74zi2am1s6aWfz8TJpk9nHLjtojjsvi8DVbsyyew43B', 'unencrypted:edsk39GkXVLvmspdB3mRidzywrRFmLRJj8xx4GxcsHUvHq2LkJWGc7',
                                  'unencrypted:edsk3M5KY9CSdrsYRRQcCs4WLpQ1sgGEmVmgrLaGjj3g8aDnHxwCeC', 'unencrypted:edsk3J1EAyFxdVnZuHSoHar6nKLjZE2HFrkvrWfzGf5A2NFmoqK1Pv', 'unencrypted:edsk44GzvVijg5ueLjQPL6wD5kjrGGQisvViWwVvAaMunKgPVB6Bs2',
                                  'unencrypted:edsk34XgXUc2zijj6JeSiDXAA2LcDfFfKaQNm1rKoQhB23kkCgTAHh', 'unencrypted:edsk3nFcfQtdfuuV8Vp7H6FxxwUhrApir81uGAA1sKSGbLiuhTxzdx', 'unencrypted:edsk3TmrnTVDERhMyjpfTZy6ZMuJ63uBodjLV2cH2P3CgnjPBfMAYs',
                                  'unencrypted:edsk2jrkYkKYmEy7CWnribo9Aq2XL6et1B6N9FNaRwpgJg62EGPnLP', 'unencrypted:edsk3Kv7TmnA1K4jvy6F6vv8fMvg4K92EqMaHkEnzuC1X3hpGAd3Bu', 'unencrypted:edsk3UmdteK3nokyYdGxkaEEZ79mWJsmKLr9vUp4vWKdEzJ3mTyJp6',
                                  'unencrypted:edsk3Ae8tyPe1uVvvz82gG8VhyyrY2HHRoXfiFbEPh73i4kvbEzu9i', 'unencrypted:edsk3Z8qmqBpQyjphXpK2SsqsmhbPm3JynvdgBA4SEMpkz5iggesAX', 'unencrypted:edsk4EbvTAL8QEB81mBxRfyPKfJWPU5z9c4qz7fanMLTkJjH6qW55q',
                                  'unencrypted:edsk4KTLgyCKBdjeUwa2cRfxQ6Ha9AZHYAg854D3UtSgVCWwsQom22', 'unencrypted:edsk3KTuoPu2CxYPQmeeu5d4y4fnwi1Xc14iBVopEEpfNsFzJTCShS', 'unencrypted:edsk3vadfAnnAgwDQcj1Vhd71KeGx1eBGWYXyahLaUm5dEKybedXhZ',
                                  'unencrypted:edsk3NUbrwDQkJSctQwYqNdxtQa1Y5E13MzzBwBSop16GRA7hkMsW6', 'unencrypted:edsk2vaTrDG53UycXgNSVm8d9qpGWwyLpdUkF4cW1SHgonk7gM4AsG', 'unencrypted:edsk4JJq6FY5dKH9MAtzX6YVMQzgJtNMRGKkJxJYgFUbcossviyYGe',
                                  'unencrypted:edsk3iGGJYLHLDAdfPrWPp5zHqvVPDUnRJzBccTzqtJ1DWFsvsfGuZ', 'unencrypted:edsk4ACMaxtuMizKPy6SR9GPygfLm5177QrDBFMXininPwUJkDvdzz', 'unencrypted:edsk2jyU5BMbhonN8AWJPcvS6nmVXrzeHbu3rtFfUFWdAwtf2ETqUF',
                                  'unencrypted:edsk4WSNqJ5tmmCkhFMoKWqmvLgs6DHZAjh6AhMrDN4w3JkksNqktx', 'unencrypted:edsk4VC9NpQpduAw1D1QH12Q6whVuNcB9m86U9FQ3Xramzje1LMojH', 'unencrypted:edsk4Yg1REYTok3kuqYKKjWKESuEfyQLrHnpqnKyPBtVjnXssK2LfP',
                                  'unencrypted:edsk3uw5W5du2v2jLiK5TsvUt4TaWPGn5cZhpwXqHouGF8iuiHdtYj', 'unencrypted:edsk4TawgWzwx7DQNXMf21e26kFsuAhGsNQCTSRXBGwoLZPm1cBpg1', 'unencrypted:edsk3irKzNbeuCQbSCNBtMarMFGfcCktfBPogkPoybr2kZ1YmeZvLs',
                                  'unencrypted:edsk31UNe4NZSRAMni7ycPdHid9Cs4i6xWje5ymSV77UjNS6E47Tsg', 'unencrypted:edsk3KQPKjSsn6sQ6xQ4qftA5BfDfPr76kLhNeLtamecy8GBF6JA6N', 'unencrypted:edsk32UoPMKU3LfZQ7vdZDCDU4uUW4H12AfME5imck3aC5ayNBqTL8',
                                  'unencrypted:edsk2z4A7i6HdkHDn59VwooJhGKt2L3DG3JmP4uC8f1MRc6VACtCW7', 'unencrypted:edsk3JFpCrN6m8kup2chkg2GxtAh7pYjwWXMJwb6RaGDVVDLzHwsCV', 'unencrypted:edsk36pwEuFw61SwiymSBygkt7dYu39UUexRfe419vykVZHQ9DDCVq',
                                  'unencrypted:edsk3HUpysD6ituLtk8APGHDfMm1R4GyE1cv7791BPG5QtUQySVE4z', 'unencrypted:edsk3D6cqMaF3u49oKqnxNwS47UEQKrzMwuVAqeUG1k1mYGSxBS1uH', 'unencrypted:edsk3HTe4F5XsytDA9H6JkDW2wZpHFcz92qo5DX2QyzVWeh8PJUTta',
                                  'unencrypted:edsk2g7HKku8923hZVZYKKX9FkHBYHor6sX291UcftShNGMApWdho2', 'unencrypted:edsk2n4tXvnoAj1nhvk8pF5TSV2vwb9kAYVNQ2ToqH3aHT6yLVJYrs', 'unencrypted:edsk42nETAZ8wLjShDMEZcbnHUCqnrU8eYGDr4nFEvZJXi5bCFrq8V',
                                  'unencrypted:edsk4HnebQcYyqSNQQmanYSnukpdmWELfH2G6sRHSUcG5v32XAfEuE', 'unencrypted:edsk2m2JZJbWZ1UzP7n4xkYLQyuCTF4KQHrcWFtiZVPgtBGYRY4mGM', 'unencrypted:edsk2hiuPyMAT2Kv1hP66kzU6tTNWnwW4f495iBY9j8pEAywvudPYu',
                                  'unencrypted:edsk2j6K23UCt1SmPpeUhTkdi6YcU81ntfhfJKmMk4oADYSmXHozJ4', 'unencrypted:edsk3sQmtye6boUFN1x211PvXJKWtJ8uaqEDFX6mxRpMyLLgTadD8Q', 'unencrypted:edsk2hkkG1RvRdWTSMdyiLBRdbZ79jzQBmU8Bb54Ax9REgUeqdbQmR',
                                  'unencrypted:edsk3FxXT7aAKKCLeiDe9jNnNNJaQCV5qjTBaveGjpwsRo8XUvnhML', 'unencrypted:edsk2hbd3nZNqsuLwpGPSKTxqwGMKqeyoJw88H8uvD14aEPDXNsSYU', 'unencrypted:edsk3RTPcnsXFvyqJkmB5DEJBj2jykPr4eUwUmZhP6f8m3eyqg1ETD',
                                  'unencrypted:edsk2iJTZo9yRMfE2cUXoYyD1C1SktfQasoHEdBdRJT3XuVVfMwoGG', 'unencrypted:edsk3xSu3RAaSZWSbfu81pmkiW41a2AYiYMhQUmwG71wAUAf8dv7Gg', 'unencrypted:edsk3CBFW4BrmNtU1ncd4N1Uj4bMgm9ZPpkokYuEkARLMKRE6Q5nkt',
                                  'unencrypted:edsk4Rt3ozfpb3Lz6wmQdno8iXsVMPH5TXsqZRwuogmLhAejBZvtMk', 'unencrypted:edsk3sALMEetNg9b6cznqsCjBAecnVQCGmSDEJKGANzDWQLZMfbQ3m', 'unencrypted:edsk2xaP3QTFX8Jmmz4WNyHuRWYAmo2FVgxV4SQGdwawvWzoz4Pr9k',
                                  'unencrypted:edsk45CLEMEbnkek2FxoGwS63DMnWiEZ6FWA2HFVfHWC243eKjoMUq', 'unencrypted:edsk464r63PNc4VUdhCSt6BesTX9sTBuMUVocjr78xZ62rwTSjM2FW', 'unencrypted:edsk44VxpbBiVxhbF6JXcXqzVo5JXp9HiXFeg1sG8Xbec4x2twroZQ',
                                  'unencrypted:edsk3PqmCMx1BgoupqudSS9RCb2yXcP3J213S4FZ3viHD4HnEdATfR', 'unencrypted:edsk2xFdL53b2DHkRmUbmsRk6oQRkMm9hPqvD6n41vedabomCrYq39', 'unencrypted:edsk3m67SsqhGxmyfcx8tkNNw8Hb18GuAmmLLeTUqsxUvpwdv2ruqQ',
                                  'unencrypted:edsk3RjPWgtoh1rop8PxHWVPBsNNiiNt9Si2Wita27vsyiAkQtdJdJ', 'unencrypted:edsk4La8QQMeJXAHh9uxCumyTryCXroa92hxRSatVdZzeHz2LxbUnr', 'unencrypted:edsk2shFn2YY5ShWvmEqxxsRVeobhWqAQSsY48iVWsgZ3xojzHMie6',
                                  'unencrypted:edsk4Pd5DwAWJAS2DTE5W5wkbpXXMtUpuy14tpjQ4p7RFAVRJK8nop', 'unencrypted:edsk4DLM5ZGEwFFRdkuP6Cucyeer4orV8S3twSMA1M3UTi8rYtxcWN', 'unencrypted:edsk3ehyNJQcikTwu7mqBfjRNGb6Tccjm3Y6n8FfpdQ23UzpXvsu8N',
                                  'unencrypted:edsk3iaZwJTUaQxUQCnYtg4jefePFK3qEgrBwnHzELNoBJerWa81WD', 'unencrypted:edsk36PBKXRdSSnRkMrrbra8xBAkxEZaMvqmoeKNNU7rtFqnpiniFr', 'unencrypted:edsk2itdSb7xu524fT2iCSckyKWxxKxRA2R7RxDEzTZ6ZU2NeRrwhF',
                                  'unencrypted:edsk4ZtGTmWypapYVUpN8jd9LVc6zSpL3dK9Rgf46VE4sfg8g7okrV', 'unencrypted:edsk3esAod5LXe1vkCwe8Wu7PfP5Bn7hgxqiBNuH4DrisAzfc54BFb', 'unencrypted:edsk3AHxyZgfra7WVaogzC3nkkfQAqxw6nV3syUpRtzFatkLPb1fqd',
                                  'unencrypted:edsk4USJbEPn7gxDQfnFkTntYYNxqPjzaoZhP9cFn1RvRCPoT6jbVf', 'unencrypted:edsk2vmbJ566LnL83oDGeyCuQTRJ88Eq6b6fU1cmUPsXsjSv43uiA5', 'unencrypted:edsk4NzyyUVCsRXvQ4wcz51FGQm7z558jAUJxKTA5A7Ww6KBHeRGbF',
                                  'unencrypted:edsk3ZAXeuEmEppu8rZeDwE8mLvV61F72hKjYxnUSUVrZ4ESTqLg4n', 'unencrypted:edsk3z5vF814pFNMNbzYgxsK2eJq4DH2cdPK6U4xGPaLGzTthMZHhA', 'unencrypted:edsk2jtGMkAFxcRJ48uwDshxicL5zZuXE6x6szE3Du7aV7nYAFmaTy',
                                  'unencrypted:edsk37rRggrZhgQ9PHzzbkLNXuNAQVW4LSfVgfB2YRnF2QBtHJoE9d', 'unencrypted:edsk3zv5CPSaWrkK1JM5a5V3GEYgD4kWkF45SDCGWGV2TKsUJXu8BP', 'unencrypted:edsk2iiSsbrbPHvRXJCvShWkTs73qyotCFQ7snqXB4LC7v8QJL2vN1',
                                  'unencrypted:edsk3mr5uRdCkBhnQNr6cqGriC6WFu8SPLk3tYTjwMDSGFfARuxzYU', 'unencrypted:edsk3j4zG3JtwXAegsuoFerwgYkoQB3mastwQ25SFTesF5Rhgj5Zk2', 'unencrypted:edsk2mj2hSBfkugcDwskDnC2drCGmwGMxvdebyKDmYQgG2KwVqwW6y',
                                  'unencrypted:edsk4H98DGHmABxu7UA6fFs2tuQsUpuH7rRQmdCYE4NxkicHqbEmGZ', 'unencrypted:edsk39sX9vjVDKn6WNFymeh1QaX7H4v35FKjFbnjyXRLcJ3xReEe8G', 'unencrypted:edsk378HFxoWzQZiSMN8atFPeV3UvjgURfvmi38WZfgnNXBQbNUpXD',
                                  'unencrypted:edsk45vXW9Vhf8SNXg4h6GyvM1CUi5UbE37uJmLJeYbCRBBKaB3zHQ', 'unencrypted:edsk3PUVNwPaotJsmJ8fGht51QLgCvR1btkYY2VRbkg6ScABhWLQxQ', 'unencrypted:edsk49a2EEXBQv3zs4V6a9JgmbzYhYquctCuzp6P8b5aGUm1dcv7uj',
                                  'unencrypted:edsk4GPXrB5h9q6ARm7rPAvxWd22nxxaVPf6ejFTpJRbytautifUhk', 'unencrypted:edsk3NiWyPFZK8FQCxVMKAYNujxKpQpfH9MyKZYrdAyNNKqLorrXPx', 'unencrypted:edsk4CETcMYbXHuRDGwpwRFTscHD339GRCgcTYES6AZthykKT4HowS',
                                  'unencrypted:edsk2myViLAdDfsjBRTsfaMqH8Et4xKSEdPpud1KTBJ1sNvv5QKb1U', 'unencrypted:edsk4agYi9fzhBvu4ARgF29kAp3ze1AxgKbbtQuwqLNEUw4SsYHjGA', 'unencrypted:edsk48wvUCFrXVNj1z1HcEMxrpTmYed3CDefCLDwER5k2BFT3uAm5t',
                                  'unencrypted:edsk3p2XMX6v13TxbzhaH8AXydVd8V9HpQym1jQwAGKtCi1n4ik45R', 'unencrypted:edsk37TJ2aASxRJpnyjq6CKygkQKybyfCjYTRuhe5QYgu5hJuVLiL3', 'unencrypted:edsk4GPCAZugjryT7rkDp32ApijLeKrgshjhMsXjT5NDfCUPbemcJ7',
                                  'unencrypted:edsk3DsCTBFuxNgD59UQ37LiD42Th9myyo6eHFqCHtGL2geRW29e6r', 'unencrypted:edsk4HRRSj52NJaag9qzwPDqQ4Xdcsmxt4j7PeqykoWsKf9iywnZdi', 'unencrypted:edsk3ZJqQwFpgKmSYtwCoseW1xPAxD3LYDQ1SAqkT6814xMSzjNT2f',
                                  'unencrypted:edsk3QVSDoKuSzDkkKnSMhyVpk4i3UohySrNZaQ6LLSnyzb75rDBL7', 'unencrypted:edsk4ZBNNHoyhiTiZgMkvh6BxdFqCcPGDHyqA4rqS2ZZQt1wgpFPnp', 'unencrypted:edsk4Esgp2L2oCyiNTd2PMMnfhLhtYhtS1GG3nTKagXJxDgD46Snx5',
                                  'unencrypted:edsk3YR8GQUDjM9ioZ5vidbPoha8NLks3dFRWM5X4JF5XGu5TycaoE', 'unencrypted:edsk3QuE9d8PTCrcBLG122L83dHmvCEPUx29omPVJeGQDkJmJLRbXX', 'unencrypted:edsk3VdHH6jeCSBpPPij7t1Fft3PtPuHGptajVpLrzjhpo1eTJmamA',
                                  'unencrypted:edsk3tEL4z4F2D9DJ959YBkwnxiUPQTYyU3rF3djPJXNMBa8kaBGwT', 'unencrypted:edsk49wBPZzsEwhwm2hq6Gaktp6U9kMVcXpBMpDKtXdYCU9NcFJiTF', 'unencrypted:edsk4GLhfb4r31mbfGdwsop2Q47SB4irMFLR9RXg7PyP4jQvf3fb6y',
                                  'unencrypted:edsk3nALk3h3S8SmzYKPfbm9Q2pJkkqdQBEaAdAH4vMPjyAPxHjTqL', 'unencrypted:edsk3dEqaTBt4yJynxVUFgmtHaZUs4iMDugKvVpxFZhz5zzteeQME5', 'unencrypted:edsk4Tgcta19hDNdhBQgQ44v6NNEqjZR19BvojuswSkWsJKrWbvK9e',
                                  'unencrypted:edsk3nVq9Sa8YDzZxm6pqZuAQBZ4SNRjgQ73otSEtDc12LDDKSfqRr', 'unencrypted:edsk4MY89jT5D1kY2cqkVQ3wdMeFeNcfJkTyBhWeS7RRpsX4SPDDPN', 'unencrypted:edsk3zcHMzYAFyLRSYgQcf88DTDcY7vYzZjdUfzdfGGxweZvJmVas6',
                                  'unencrypted:edsk2i4pn259QQqvbiuBbzUeDQNDMQbZ1egLTjR3Ks3Bj1wfBTzi9R', 'unencrypted:edsk32ypcjiZviUg9ii1aR3moBDJvjSNveYALpEU9av6wEucQqXmHP', 'unencrypted:edsk4Am8vYxFpzsMdhAUogyDdPDzYhL1BYkMWUvcG1qnkZDU5FoqmP',
                                  'unencrypted:edsk4TR3WkNMim9s1mYnoySEzyEBVB1C8mDgAQMhsRj27kkAGifwMj', 'unencrypted:edsk4Fwh5m4bijUFMrW7ZfUuyioidtUivVtjfQVfwe8VJxnZW4wCZM', 'unencrypted:edsk3QWNWP2jUuqsgHKAbFu1kYku7Rh5qZgaNv7pH5F8uWWgw4RihD',
                                  'unencrypted:edsk4YJhBoC4VdA7KmEndo8z1uRLqmvB85T5faJmhHGvNv6fm9uSh4', 'unencrypted:edsk3RiUpUuAji8caeKpEHYBT7HhbwsVakHkxcRFZGDh7Z1jQParRL', 'unencrypted:edsk4X3jW9KrKcQWd4yaU4YaDvuG77m98JqXA2qQAtis1sXjVFQMBb',
                                  'unencrypted:edsk3K5BBQ6dPtxDac6DKTzA4gnjUXWsXy9swWnB7wKC6TASFcc6rH', 'unencrypted:edsk3L1jEat1NTzu9RLE7QpZ3dH9U3FeLgobDwDzu3LLsnuKMLnSTL', 'unencrypted:edsk3kXFXFLirvNsLJaCFb16ADV5Ds3EZ9mWj3mTaxnE6sjjpm6Z4K',
                                  'unencrypted:edsk3xWTsA2qaKniMn9ytbUEbavzwScvstcmXyBhM9RckQUuu8Q3Hp', 'unencrypted:edsk2obkUiKTRwtrDdm8Bd16f1Z3exJe6VYFQ4vB8CECWnxPzCWZQF', 'unencrypted:edsk2uiDnsaBjFx1mUYfo1TdqYRjsfbEM8LRs3PJZCABGK66Ec8fT8',
                                  'unencrypted:edsk4EiGkBQFF6wraqvUruga2eiMXprJSd69apgZM6dj85Ln1PXzsY', 'unencrypted:edsk3X3MaGaBwr9ibE3yLjwKyQU2W1roJN1KgdLDy8jqUDYUr9zVNi', 'unencrypted:edsk3Ua82AnWXnZC46iKKoKzTbcLbw3gjih7jhdfmFiJEiLiXp62vZ',
                                  'unencrypted:edsk3gg3uCkofmJJzWRHvNQkReWnRD1GW6bcJcfYnSd4thhzHNHsK6', 'unencrypted:edsk3iD71SbenChTxueDnRtdvXJiLgSyf2M4y8kzZSiFhj4Lh4acgC', 'unencrypted:edsk48Ch5FSmFDRghq25jjBbMZr84izVTuVYFpPuwFNyQGB23DH88M',
                                  'unencrypted:edsk47akJGCkEWSHG9znzs84PxSALx3x3dBmA6Pa5uXxVtb2KTA3Fy', 'unencrypted:edsk3rEWKoHUN4LKoUQ3P68EzkdcFdXfEsCpJL74ePhq6GgTkA6HRL', 'unencrypted:edsk3MKJuMz2Ygg4NdN8VjZ9kpP7mkvT1EP5kFCRacaXtTGXV1kH2o',
                                  'unencrypted:edsk3iCgtcsh3ceveXruvTZveJtT8Ty4vaeLTTnWcwgmDt1URh21Rn', 'unencrypted:edsk2wTSQhMDqUT6L56DsQGVKXk98F2iPZU3XivZ8h1VxkvJQyq6kw', 'unencrypted:edsk2tjmiFjUKL7KZnfwCrzku81pX53SpuNjQf5NNTjHrtvCsXu954',
                                  'unencrypted:edsk4Nk8pN1RaN62sRSzjFzwjGkwXomhPDEppRPwZQsG5ZWuqQBMnm', 'unencrypted:edsk4LcMqsCA71ZVdXWDaAAX8owyyL3XUnwjM2zzDTZmVDUUNFkN4u', 'unencrypted:edsk3ThzNHhR6Q3WtvAv3HtaNy8zvWwJ8PKDQRirtgEM2eATgTk8Jx',
                                  'unencrypted:edsk3WQSBywqC4vM2etr34uocb3B7HCUa86Fo9d2CVQtcMAjZqmA56', 'unencrypted:edsk4JMdXoDGX4uGEuC1LCJKqLT1aZnVzwC999B8q56nDM4cSu4KdH', 'unencrypted:edsk3e5BNDsfyJcsoVrRXGZzCYWmV6ztj1vPwvST2J7vGBF3GiMnxN',
                                  'unencrypted:edsk3JenrMq6BLDfwfzueb8UZFj7wDz6tmiByPZTrLxrcEngP2R2ZT', 'unencrypted:edsk43A2P8L2Yiuj4VGQHbk3q25ecAD4iFX9x4knH552WWCLmgKMt1', 'unencrypted:edsk33NHpony1PrgWEzc6H4RCFX7YaGgknzFuWxZFv2vEs64wWYj6Q',
                                  'unencrypted:edsk3MXdavqsmJkepCQkY6uWJgoLi2gKNjCnKUhBw6SAfHedc438DN', 'unencrypted:edsk4XTyM1tzjcuvFd1FSVioPQ5BdcYi7ja2pxs2EVVGNSowAuz1YV', 'unencrypted:edsk3mdTEuiR9wgRkg1hHmd1aBuGLJBUCLTHWEJoPubR98ikeB93gN',
                                  'unencrypted:edsk3NeU6tEpdDUug52gc42vv7NDQZ4YbKMTcrEAwgGGKTQ1hBU1By', 'unencrypted:edsk3G4owCpZLY2disW6oXGrKVAzQFhxbdUip8DTkfVfnhkBVWAfmH', 'unencrypted:edsk3EotY9CPzf7roSG2Z2Gsuj8TqGr1Mi1bBjZQaqGyyrEPPePpwP',
                                  'unencrypted:edsk2zbQAKx47m12DbaU1LX1yJHiMChqUMVEZQR6tGSFZtAXs9WKmx', 'unencrypted:edsk3TtkLvL6Q3odd6NLhrCZKPKwPNFSnCXBdw8tyZFXgdQ15pS9gc', 'unencrypted:edsk4TECNkNFcVLysrB3kLSA56P1oRsoeMG39mPZdSLiU2Bi6EPPS2',
                                  'unencrypted:edsk3envF7wd4TQzvfnctH7Wdye3sZ9bkqprvRkcTcS8LGHaV31xCx', 'unencrypted:edsk2pd6hagWP8Dn5xQsGY7oQ86UxjJwgMP82GRTV41tMjUv4hAgS4', 'unencrypted:edsk3Rsh4KYak6UFrjk4tCNUTSQUmTH27SCnWwX2agzKoxARPvQg1o',
                                  'unencrypted:edsk3AXM46mL13E3h1AU4QzVT4N9oV1pvNKSf1SYbTMB1qpRbeXsAw', 'unencrypted:edsk43HsBc3KX5swiS7f9xUJtuVXZLYyXVVZTXxiR1JyiADN8ucnDH', 'unencrypted:edsk3CBQNyTha2GLZQJDGa1UQvLq3Z8BfccMyiahKPzELAAJFB9fcu',
                                  'unencrypted:edsk3VP5k1LSYjQWCBnzFMokRcxe7ABVCgHu1BgC8hGRByKRc2SbiG', 'unencrypted:edsk3tupgypwe7NTikgb3BexxTJgniugLi8jysUiXenLfsvmmPEi6N', 'unencrypted:edsk2p7Utcayhp4zUok4pnB2zFpoRC2TiZnKFzaUnpYX27xo5NyPeU',
                                  'unencrypted:edsk3jog1o8V6mFVjsvkN3P4CMcxAt2iSd94hHnMq8S3DxBSAik8cg', 'unencrypted:edsk3CoA4PSfn59hwRjwRoe3ZtjwdyAbBnZT5aCLSmj7UQ6HjEtQqt', 'unencrypted:edsk3hGqhdobsTnRat2KE6DM2pt9uAUhyC3S2XqqVq7aJoojDn8iUx',
                                  'unencrypted:edsk3cbbYi2ifsp28vM9tbtiHmSB569nPDd6Vb1S5B2hXCC85X46Vo', 'unencrypted:edsk4WKTVu5HfEtjdnqd3CeM4nWWJZfyVncwPutXRk6M4F7CbpBP1v', 'unencrypted:edsk39a5ekTpZqVqRjtBYcfXW38puUttR2z7YtQ9PpZ7SQj6b8euZo',
                                  'unencrypted:edsk2rRX4kqVaKEX3uQeHxJwZMVEXfR976UfHJCW9qp3dZEWcHcNMt', 'unencrypted:edsk3wLRzotCGzsKNJ5BJPh7obWzFQXmV3nnv5nTRLJjia5Z6ZhNiV', 'unencrypted:edsk3ag5286cncGLvWDUGAaMPusUDcQtGphWmz2WBjqaQtgtGrd7UT',
                                  'unencrypted:edsk3t1b4QsUpMPMt5x6ycm3TgKJEqfu8XEL84HTLKvcrC8n8bZSAZ', 'unencrypted:edsk44TA27And3Y9nGKAR5K7LqCXK8QKufbdJQkrNxAeZA4H98pYFE', 'unencrypted:edsk3sHWDPt67itGLvWWj3dP3a8wLAdjJKVn9EtsDshyWRnk1zihva',
                                  'unencrypted:edsk3r1GpewLTH1H7AXBRCghzsC1eBAPo7BDK5X5FrZB4jHKTfMJ92', 'unencrypted:edsk4Pq6Pdo9YVpbVQW2ib7g68hy3Tc3K4AX2d1w5SbjXPXW1KXUEk', 'unencrypted:edsk4RfcRZ9C2w2B14Raaed16ucqCfC5d9ULDPat6cjjCddaabCXnG',
                                  'unencrypted:edsk3D1pvCwQF4UQcuZhL692Z62j6GqVj7WjSj8t2zgyxQCMhBji2z', 'unencrypted:edsk3vwYYZrXNife72kAgEtfSxRC8DoGXAMAYrTbSz4VHbykU1jNGs', 'unencrypted:edsk3C1Eu2H3HHN65FpPCSzAkPYAaanXkZ7JEdhnSPpsjuezAkjUFL',
                                  'unencrypted:edsk4FFnsN618EbHE3C8WPV5Xtv9UxV7ZxdAyAbcQYRf5XwcU1s1nu', 'unencrypted:edsk47iu2A7DTr65q3cHitKvgjSzFz3WPtemEo2VdwU7JAZzj1rCgs', 'unencrypted:edsk48zbW8DVY8FKPRxgio5N7MQxLXUg7ADaaxBggeSGNHhofhG5s4',
                                  'unencrypted:edsk3T151BTYpiMdrToPM5soXLgwCBWYwSzvUWbdCnV59gDb1qbRFk', 'unencrypted:edsk3ELP8TXY7vid1SrthGvhyxSvhmqxsEcxcZe1RRbFNcWL949vSd', 'unencrypted:edsk4ZSHoVdzVU4Ca5QaUNmAemM6m46Rjd2GL9F1nixg8JFKzGZnSk',
                                  'unencrypted:edsk4UA3G9qZgg9992dbXc4cFUJbhvwCJGM4XdHrvYghxhXxqsjKBU', 'unencrypted:edsk3JP8kfFnGzhgtJVsRdLE23w3iu2CakzLdZqyZa94CE3RVeodwK', 'unencrypted:edsk3hCKjMejRRiNYKu4BpFbJTHFkLr7ybZCfAb7fU52SEDU2AYcj6',
                                  'unencrypted:edsk2wkXxj6c1ZheaQP9mjUDtw3P6QZ5RAHT4GkECDGhywfyw5281v', 'unencrypted:edsk3Ys3JZTSKJcgJLkSEBmF4bQDGqiMkac64S3xSt6Kf1n4mg5TVP', 'unencrypted:edsk3GLRttPZ7GoK6LeLSW4kbSkvtEWijJ4VkEdrPQz8p1AfWfybBx',
                                  'unencrypted:edsk4Qfw6WMwoEqQok6cMeXLQbT1wME2MHBFXytFcn3ggSPTtPWNMS', 'unencrypted:edsk4WBNpWmvtzgUoJQ7W1MjnEoBSH5yMacxKYqT5DVhE3gwveuLa6', 'unencrypted:edsk3mMEu9xH7Ve25zbbLDVkSHXHNUEgg5jfL2tyx7Ts7Q2TVnu5mr',
                                  'unencrypted:edsk38yS3ML5cbUt9ctgSGCJkEZtmqbfkfP4TCLz9BEaEmypqsySjz', 'unencrypted:edsk3E5SaXoQH5odwdXQ7HPeANj1WeBVvto9bvWJrjRvaTJ76MBp3A', 'unencrypted:edsk2rRVxi3ebnXTJXDhqgB4h13yUfvJtZB1eP23uwATTyVwuP3img',
                                  'unencrypted:edsk4ayVVtd2rK6265VgTChY4uYdjF4BRXXL2VGhZCbGTvFPf1zJAH', 'unencrypted:edsk33VmxvAhNZgUmz1xgNZHMVRaFHspA3b5Ln2zHxfVXp8u8YMDHi', 'unencrypted:edsk2rtZH1MLaDUbVkBX9aYJJHz4X8AQgJjPY5cf3mTBPWXxraAMdU',
                                  'unencrypted:edsk3hxFBfiRHRteJeVUNHJ6GsNyoQZ4gztnLXrz8U6gNTGEiF3RUn', 'unencrypted:edsk3q9y5ejvBrmDVXC6wgxm8rEXKR6X5sEoX39xaLhECNb5kbk81f', 'unencrypted:edsk4cdxTJ2VmWLXYSShBRWzwNCvhpoAFdYdTNnsF9hFu7oY3bXvPs',
                                  'unencrypted:edsk3fvBAxPvdbMBhgPkv9YGqJFfMjx8pYukZHbYrEbaoSujsqcpT9', 'unencrypted:edsk3JD4DW3bLqeyjFf3MhB7Av2stfwQ59zHC6DKG97uw4GQQ1jnXv', 'unencrypted:edsk3xaZAqRAFHFTM1U8oxB3zBo4u5LsjsWowT7bqLTMW5tWY4Ztrj',
                                  'unencrypted:edsk3ZoFJAvtSS2RLHVULK4abxvRh9GDZWs1Tsuytk6qTziRuPFf9C', 'unencrypted:edsk3DM3gzDmosWKZKGUt43ztfW5oLjRnQtr7NnkNTNjFUvWnpXiir', 'unencrypted:edsk3Yy6N6A4fU5JnUXWGSmg14KEMXHRYJtYZPTXfkZoh5i98Ryu4V',
                                  'unencrypted:edsk4NYi2uhgToksd3FKDJ97iao78fMzuaE8cNXVjDDuacb1fx6Gfr']
        config['public_key_hashes'] = ['tz1SyK4X7xaarzjXoQmzjh9toWGMn9NRBv8t', 'tz1WFYojFoYHjEnMJMN3inPdcqmdacbkDm93', 'tz1iCpoTPNvTsMqFvcQwUmCmudHwx83qhQY5', 'tz1ZuAiRGaEqPmX72P896AFHmshTrdACm9ap', 'tz1N95ZC48Qcm4vu3KG12LqrGTH3NbR8K7Lc', 'tz1SLBApLVpi5zeTCkJfLjcJtBRuMyyYZ4GG',
                                       'tz1eJpeovdwSDrhhH251Eyo6ZznGKvjSMr3U', 'tz1Lr9SZnwQa2WeTEA4oRpMGpLNdtuupre9j', 'tz1gwt55NVSHxsNd8Nw89BdARmPoKvtStuiX', 'tz1Ys2nxLUq3MSisD619B9MqWDy9F2yYJk9j', 'tz1iMY2QbarnHrAq24ek6dTP5ewoMD198DWi', 'tz1iXUgkMaWJRfg3FsbHW5KApvqmbNunbirL',
                                       'tz1eS6MCwFMH8E3BVukjMMtLYUMqsUZxefWk', 'tz1cEoD3DnyrUCaDe6L479QfJ7NgLxtrtCVz', 'tz1dFz4pvT3Fu3dVUgcGEBFvU5gyoJg1YWma', 'tz1MWBVo3yPJU4jRFudRBaVB2xpTdELY6Chp', 'tz1f5T1XbW6YHsKrGFoxGq168g7EBdNQGd87', 'tz1XnGjFYzkcgcN5KZ1x1AqAz8ygYhoybR8T',
                                       'tz1VVkS1X7RSs7W8Qb4bAxsy8hSAwYwcnrur', 'tz1PTiaerKxLQZVTRooBDLvvpcv46ridKUtF', 'tz1RSWBucF7vjs1uxRWzQinP5DuosHE56nUu', 'tz1iVWrQQrAmTnbWQyebFJ2U1qfqZrKNRpLG', 'tz1dozKAV99CHn85AfFHpJY6YshE6tbUsLaZ', 'tz1THi7djkUNstryNJfA5uLb5HG4pTX2qrnp',
                                       'tz1WtRvrkmCsq1GUCB4QwsXBtgqSsVAUb5R8', 'tz1ZJaYfqjug6fWn5GnwdNcXfH5iD6EBYC4H', 'tz1WaVPkwjPxeQAMABeZnWcVpjfGZUXSv3qf', 'tz1TGCGg2SUNNXFzNC2psGycgYUuF85r7qKa', 'tz1gZ8XKkZfhiGDtFDpBkcGBVDi2kHJZHHhF', 'tz1hr5uCDMrTJ96ynBsLDbDgcdVPUZmzE9GR',
                                       'tz1S61orRoio3P29286X8LRLW6HkDxWMF3iK', 'tz1LrDo75J5Eypg5c5veEkf1XkYXVbqrqX6b', 'tz1WruhxAQrRTKpc9pTF5TMwYWJEg6Vs5QUY', 'tz1WMhHVqJ3odxPCqA4g27kJ5i6LWssTqWkp', 'tz1RaapFWA3Nr7SJ1RKCJJT5bmuH1t6iRqjL', 'tz1c44ui6SocZBB7pQuz5JthdYpZeEqP67J6',
                                       'tz1bYMfpz6xy5qepbEkZS4niS1UbbPwScEft', 'tz1NxQJvXmvJb6AmxjLwb7QQwHnsaEWwdCCV', 'tz1VVFhuUufdXb3vxW3yjuxQG6T9o9o6R44S', 'tz1PVjASAhGoDiBDmi2Us24QjWRSxofMSJB6', 'tz1YvLjjYLH5rho19uSu6PZc2CB5KJUyYQMe', 'tz1TbZtKPrCEBnHcm45mu89tU8j7EiT4uwTN',
                                       'tz1gok7pCE3VwsCPvTyxUmfyR3X1216QcYKL', 'tz1dt8oFjdDjFLjAHC3gRCWR5s6EyLvf6GjA', 'tz1drn539TdoCBrQ8yHqRRCkhdfxjoLXtwsb', 'tz1iCqNJDP2P1MSKd3jpcvdk7ymSjeLfBQSm', 'tz1WRvZ65zhGYZAmZTL84JrzeqUfNMX5cdyC', 'tz1ZeZZjNcm6x85McNJ9fLGuDq1aB6mTsnyZ',
                                       'tz1bwnNfXdjCGUBKd38mp4BqKpinK4GRJL7w', 'tz1U6GmeBqpxRfutWcLh8V1RXeoY7mtfgwz7', 'tz1V5wKAntS1scTLqymfHANEiXLBv9dUjtDt', 'tz1eT9Dra25jHqyBZukMpZnNa2dLF4iXusAC', 'tz1LrChZ2wfJNtqLv3P25hvGLWhcSCa9Tdjx', 'tz1ZgDfXmSGiNdjzcMVRW6NcGv2hNVRiRX23',
                                       'tz1WeCCecaUyTrFPZgv1pXAcri3MvVT8HyL9', 'tz1WwLFxAiGHKBGpWJmTsVWfmAne63TxQGQg', 'tz1L5La4WzVeffZ1RKRHNMb6cbZkFeNDD8hF', 'tz1TWt5VJ1rcU5EuME5LbwCx8nkmYPZHtjbM', 'tz1ajdfN1dU79gKiiZsNkfXgfRQEsVRBHBic', 'tz1dhD2KrQPAb4ecthL866sk7nnGrA9Xfpfw',
                                       'tz1cJzL5jxYq6VvgmKCPPycq5rqxDtGtkGum', 'tz1XeG6p4baaHpUnKQsZEVqqiAURZQn374ur', 'tz1NdSRya9DoYXBhvGKjVXVy982M5XbTcK3r', 'tz1VuYhKWxfLBnUSFyzK4TN2xQKqEZup9br9', 'tz1PZjeGv1v3t7foQFa5a7pEZDdi9FM2yxqv', 'tz1eVjqmzdTswc3ZQ3rLfeTqCUfuUoSbfFWs',
                                       'tz1MrbG6L31Yebc4pC6WJJ6UY5bY8xd5E92Y', 'tz1ayfW8TNoUqArA6zsMrW5WmBvMStPCNbME', 'tz1TnpQQt6V9Z4oefT76V7Hh2TyAUYTXXTQG', 'tz1NPeYvoxXvebCGfi2Zsfcohhhup1TBCHrL', 'tz1U6P4ef6e7X6QCZ5sm8RvRgV43JQQTHbs3', 'tz1aDPbUzSy44DbFLPAc3ZDqq3c8K9NLfc5D',
                                       'tz1e65rQtetB8h38NDnN9GVMiTSktEqvmBM7', 'tz1T9ksB6CaNnjQjwS1A5VqnV5D3NtMcXuYR', 'tz1eGZnHtzoRutybWTTKrQGHwPZVNXARNhcU', 'tz1PDBdCoREETaBTtQQtfTybDNeCB5bhmjkX', 'tz1ioLJ9FnVtqioJHaSSbA2iZT1Yzjs3DbrN', 'tz1KkUEuxNDAfE78kEZT4PWwHe2wSyuL5UwX',
                                       'tz1V6dM15ZSom3PWDiA3kGRUeha7DMrFU9GA', 'tz1VTYKtvrWQT5KpXtKCbqRaFxaLSwWJ48eK', 'tz1hoP8xzhZch6bU9CwTCsGbEis8dpY9ofW1', 'tz1cgNrUkVptbC9BTmucvj4qpb4TtffN5JzX', 'tz1f46nMwpe6o4oJPo8r65yLeztKkThYe5Kx', 'tz1MvRtbVP7TQJqcXsa9vNhB1x8eUh5bdV5T',
                                       'tz1XGXM3xSwdGTdcXE5K4VeePpAS6DyvEJkv', 'tz1eJMSWcSqEpnLN9yffPMrup1J75J3SBha9', 'tz1MmfcP7k7Dk1LVFxsuzLcQt9rd331uHaLJ', 'tz1iBtGGpAZGVrefVcgNJvZYxLYGCDc1AR84', 'tz1WxaKpX7VumrZW4uqYSBUwPVZYGm5KzHjj', 'tz1bCjqLGh1ijyJ1KkFMxAkbjrmC3U9bL3hR',
                                       'tz1gp2DPZMnzgnf7YAcyYsfsj7VfKefDYbkE', 'tz1QZqpQzwxs836oLULXMM6idMUKdkYUkQBK', 'tz1MAtDuVkWKrLPQzg4W8UipUwviw4N3SXJN', 'tz1dcx8Mf3e5JxGRdgFXRyQZaqAku39hUuj1', 'tz1VefUogyhfUfCgKjRnwKnesD95vSdRzCEN', 'tz1grvMVz6cTL7ZL4WtCHbXccBZxcs655gN1',
                                       'tz1eXa8sBwpkuHZadiauRwk5UukGPneJNp7X', 'tz1TrL81KqKbq2ejXaCuZkFnDD16jwi1p6GB', 'tz1QTuSvrT2VyVBu6Nde7YZEpq85SkCtjAY3', 'tz1amwaxZrLhSdbXL7fTYD3RD9tbFRNQ7NBb', 'tz1eFGHYyWCCzLqnhSWKzrHXVGzDjTo5KnQg', 'tz1i9wwQ7w3cMMusY8oxBja889GCkWwT2NU8',
                                       'tz1hDgqfUChwRU1GJZRDtecQRaj3aiHTr25i', 'tz1XwoeKUmRu6J8ieh9wB2iiTSx43itAU7gD', 'tz1P65WZhHxVC8z7UmBcb8uyWhEoXX7izZZ4', 'tz1eaLLByQskKXR4HQTiULePvoZN3XYxQ6Y4', 'tz1eb3mB2zMuCxnJBy7Vkd5TpcCo7qoCeaoC', 'tz1gewRAjXfXZNMKW9xKZGGi6z4qt11vj9Mk',
                                       'tz1hnXNRUhgc8sUepuFay1NHFwkLkNUQiM71', 'tz1V6qGYgqyEqfeK41sEtnsrK6Vc5ZQtazxC', 'tz1cVgcPA2ceouGg1rEHMzR8YUnbboQsXiUN', 'tz1Ki7j1H6CVB1DMjYdw1acpi1NBP2mA9kaT', 'tz1VgiaWsaZ2pyKSH8RZn7zdZQHsMFkJmfuD', 'tz1euDVeuiCMpf9KyNCMuPug3NuT1621LhhE',
                                       'tz1e7kJRkxhJdGVTMckH1pyEkSmEo2pwDuu7', 'tz1dTzmrnZyUi2nUAtrpvPw9crK8UHXZ8if3', 'tz1bGEnToKesBASYXuDtCX5QETDwNEw6NpKC', 'tz1YiD7MFV5ScrkWBF4kRdrzKdnjDT4MSaxp', 'tz1MAr1qicWAixGnLcJf4EYdnB8Tehvwhquk', 'tz1cDqt9RSSrByLoneZXi9fN8Xm3CL6f8LAD',
                                       'tz1ZNVgSynuj9855cLCGsqVW3cgHJiuYvot2', 'tz1YaU4Td1ZmAbfchXqBtNpFWBw5caG1NmfS', 'tz1X6djufPAjt5wCm5aFwyXv8U4EsPURVYj5', 'tz1Xtnaa8wJvAN9vZjyQPKsQE9KUpYQHBw4s', 'tz1PHqL7R6LZ4xzK2iUKgDEhpWLWSZsRQYui', 'tz1TiiLtUjAkNtmqC9HVM7jPv5VrJjKd9TbQ',
                                       'tz1RHgbERbpsmj3igpuNdVFbFk2LhuXJ6s8D', 'tz1NYNnAj4tr2V7vuxa12xwHbqRZ8X3Anv21', 'tz1c4UCJeHn3dMyhTjdQvVvYojXx5mha9QU4', 'tz1bYC9MFdeyBfG58FXEBx4GCMFyscViThiz', 'tz1i5KT4gSQEdTozah36pPKjBmL3S3SxrpuM', 'tz1YNSD2YQu27jh3Eg4n8xN5x1wHyXPnom9r',
                                       'tz1gyLEFNPtT1BLPNVMHu5cUUVV85TvqmBXN', 'tz1b24CPVY298YUFQzkXnqEf7RwHmgq7rQ65', 'tz1T6hTKpPkjoBKokcDK9otuaGQaGvLUebWL', 'tz1iVLrcVr5cEDhPka5f3BMCjwgzw7BtNYJy', 'tz1Uxg9zR2Y1yZ41j51KwFcmvJhKLUu94zwC', 'tz1i9vp7b6KBUTYRe5TJ7kqq4fFqPMoYGifQ',
                                       'tz1fenmxaNyMRCYuaXBifdepA6j7jKj1bvUy', 'tz1cS6KKBbHLwifeHCGk1xyA29dfbvC5j8Wq', 'tz1NjrL4mHub2BBQWm69eTecQBQQ6zTEtZKq', 'tz1T4ScSQgUU39hkHbCvqxBQcsoVKHye7vUJ', 'tz1PzZ4hQH33VSLCybmmduSJNFikrahEqvnD', 'tz1N2SeMPF9HshLGqeib9CKsnUUtK2Mvs6H5',
                                       'tz1Suth11r55EZSGiFd6Bo6xRF1wnvSXMFs9', 'tz1hDbvLwoJH6mnGU5spCbtCLMrBD3wGKuqh', 'tz1hBXCEEnQcQTsJd8JGpz79o8JNbxxRqhAJ', 'tz1aVN5NGLHEqhEJqQ5f88H1NFSxBRjvVmcv', 'tz1Qs7h4KiC8HPF3ms9EDT8AVfgv5Hdbe4fc', 'tz1cVkBu5HQxQrTwmY3xohZw2AwryqaNN6s8',
                                       'tz1hWQuqWhM1HVh5oSsHi9MangwkCss1gLA2', 'tz1KnWfck5wBVvKPxzSrDnxRYN13pxR5dUz8', 'tz1fDsmEjtpVRqVsGqV1BKx2QwHNeAiFLWJM', 'tz1XwRbsoNueE52bjDB9qY87X6vFKVpWHcLT', 'tz1cEBCzhAhu4kUpQ18W1jjxf7WJF8Wg6Pjy', 'tz1P64p3jENZZV5KR9Hq3uFwbippNA665KtA',
                                       'tz1XYW9BZGKUmMq2W2cvG7Tw8h687oNCaXwR', 'tz1S7r2snm6GtysFwN9AWmnC1PtsEvcwe9AJ', 'tz1WtQjM6TCjbaaGxwrbPAsE2E9y5y4AwkY8', 'tz1WCYqocsJMcXdEASCj7PydAA2DdQ9woAR3', 'tz1VG5CRsGwsqW2TqfWhT3ee1JmG7wKZ7BM4', 'tz1eHPzzQKzifnJ8wJ3QkNU6XZT39PDANJdr',
                                       'tz1WFQoYhTtr5mgphdME4JpUALQP9KUEhpYV', 'tz1en64HzKgmuZKLdsFADNFsPSogUCkK7z2U', 'tz1TrDX3uD1py9fCmRgN8PBK3Ltw1TBubeAT', 'tz1akLHKP79mwp9CQHKLteerpLHRHdREmDRt', 'tz1Yvu6D3AkgmTHJ4EYy3vd79NEn2xNPHnWs', 'tz1LLrBeB5qswEEtmPXJz3NLfX9ZyMxyd2HJ',
                                       'tz1ZkjdvaDwHenQUmwWgDWd9MhjqnRogVwgB', 'tz1huAK71zpFpSF7uBaJvS1iFbfJr9wxhEAu', 'tz1Wd7DNHqumdw6QW9SWduwzPwykWLJM3wU7', 'tz1YJcTc7gkmZ4GfH5fApYd2NMhAdyxP2wE1', 'tz1fQjoV9fgJUjMh8ipdMHUnoGYWKxQxxtNQ', 'tz1cUTrq81rPFHfthZfYptfM3PLxWhdDXTcb',
                                       'tz1WVpDixWxpMzNsM4evvviXGvXcCv5P4uen', 'tz1MSSgNCsCefAmNmHMuqv7Wq5cS2vezajUh', 'tz1iDqiK9AyvyAyN9tF6ii7hUphRhpNCcy2a', 'tz1NZiSsyhBEu5sNa2xxCCeqeh8bnr5TPcFr', 'tz1M3NLDKdbSys6ByTgwQYb9WWQoJs5yFjqU', 'tz1bxTwKW1Wmqm1yJj2yPhcymDCyLVLP2Jzc',
                                       'tz1LARUqYLfYY5T5sZo4gVnWqxxRCGTFe7Wz', 'tz1ZMxi7TsUWDAAdumtaAuXd9go4sdUNx1rt', 'tz1RTzVYXTtDQB7XKoDnaxthnRmAgGEYCbj6', 'tz1gof1HqyuuABKeScMrbV8CkVBMsusLLc4Z', 'tz1gcf3QQv2iV7JvipNv6Ua6XEnVgqCopcSk', 'tz1UbEKkcJL5brdEFFRqtZbRbeKHoQHq8Vid',
                                       'tz1MQiy9z6HGDGbSRds5mMsq4gpxDmh9cn8m', 'tz1eHMKjFgfSTw5CP7s8LChL6yAbhJ7dZisR', 'tz1iAKXSqS1mYxLnc2TGS4yksLWN1tKfSN3f', 'tz1hrmAmE5bzi8o92iNFG9J2UgbDguBtpjTv', 'tz1drm39aemA5rWgHjNDctCJgDv2YXtrmTHX', 'tz1N4gvpSWqjnbJpwTyB3ZdD46xi6LEMhhd3',
                                       'tz1VFczdPaFVxdyGpTuEPCY1tYdPSDJm92gj', 'tz1gQCmiB39zvYZQb3VoD2BvtcgNZCzzdikW', 'tz1eBrB6cGbzfZfC5Qdx7J1pcBziq3XVMuv1', 'tz1QCRUy4wjK5GUiZZ1GKodSmGf6yfiMyRHU', 'tz1Xk1rGXwgrTA483WDRYhZqwnKu3LFf7nfy', 'tz1cRkzxJke8gqGNB4dLY6PNUZPhBGap5Ur5',
                                       'tz1bF22J5h18Fkbr1b32vKQQTS9hduSrJo3s', 'tz1d93YPb57tudYzkYfaCBxucjv4ERQVVuPi', 'tz1fbRw1qkmqh9NyYujLYDiw3K8L6J1FDzui', 'tz1UWyE4kmdb9VYKW8yvXDq7aSFmPPv7ukE6', 'tz1XXU8Kp1BPugS2HNwJA8tDwVWR9Ufdeg3h', 'tz1a69KEDSn9PAuGZC12q8HL5Kc5Vx3ZkV9G',
                                       'tz1htq111zVVzERhLEaJcqDmgwPjxM4eMe2G', 'tz1Y5w896RB5sAvuiEC7LpckWfCchTXHz5dU', 'tz1YbkSFKdY7yD1A3LviFVjc5ZZFdH3s7W6G', 'tz1Zi2JydiRTjYKEwXwMqHb6xGAye9nHR7Um', 'tz1PWvsagDvz812UXzx2whSkjaRmLskv6m8U', 'tz1ZCiJV4h4KjeM1wzS3aYNvdk6ZaQyYbbXF',
                                       'tz1dTNifQhyaerBGMyS1hCpAiyeknCk3anT3', 'tz1UG8opiz4JmBaR86FEobdGRVbKNrfjS5Ad', 'tz1heaNbosvfQ6MQxYubUAkU5zP3jdfUgC8s', 'tz1QT6TEgM3hRLTLhZXwgpMyGsBBYQGBzfZ8', 'tz1fvrBuBLU9GhoSzUYHpFZpRwu9cm9QVz6i', 'tz1fV6WsRbEsnYkDBTvKfFmXJvFZUN4odbW8',
                                       'tz1Wvpj2V18PaJ5QvQbQwJHFwthrHJ6er84j', 'tz1MKeeM5x39EWXUsQN4KCtVqp28255ft51K', 'tz1NHweVjoQPR3ReVVAp3PyzBXfVL9Nj9TcG', 'tz1imavHT3i2yo5Ls8yC2js2mFqjWVsruqJ5', 'tz1ebDVRs2pSMaRLKcEbAioVLik63P2gZqaK', 'tz1WRPWUNqZ2Wf8zjFaMzxSGTrxDydpH5f9s',
                                       'tz1XZtMFLc5cubH6iWE6uLHZfxordk1e66qa', 'tz1YdXnxVPW7PfkBPd3iwt45f9WQZy9Wpjtk', 'tz1SRT7PPb6vEnMw7FmhAXQbcP2z5VxRTsvu', 'tz1VmBU8uyD6ZvHwdxe7mPgRLUfGwrwB6LDv', 'tz1YmpQ4HEjp4mEaJ2JtLGcKbQjjaEo1poUz', 'tz1TJiDBvpT2k5XYZSFpVj8GVJEvmQaFTUNt',
                                       'tz1WCS5MqgZQXMrEbgqq3FmySn5CUVpHvkMc', 'tz1dBTRLskCmkB7rYcYvehzgyWPQqQgzRcVy', 'tz1NKDT1BzpJhqgghK2DNS6RvXVHpBRwymGb', 'tz1SbpTfZMqb1NJMV5cdscDDeHwuGKFmznh3', 'tz1ZgSzJnHhiqungySvv87LeW6sowmmBBdMh', 'tz1iFjMg5ttKQQxfBJnYdDbvgxz1FiGpQ3MS',
                                       'tz1ZqYQ1cQvzfVVKTABEbFQkCtyjcRsYJNiS', 'tz1UoUc2NMQK9KTk1z7pAxzXbq7TxqDxyEdn', 'tz1gM2pKFo9rf3LEkYi3MAeingfA73Q8HgBJ', 'tz1WMRRx26qWkhjkGDNqHGB3YuLXB6wWXyiN', 'tz1WhUQM6VkNhKTphuqyu9XWxq2bJMTvRAXP', 'tz1gtocwSrRahKLSoBCSB6vj6oeGScKjqM4k',
                                       'tz1ehTbo7qgchiA6ifq1phqUK2sRPmYPDPvG', 'tz1Wpe5jeARP4P6g7mKWPfb8UjHdRLtZBNg3', 'tz1aRyT5d34M6RPa7nvtgwFuFAkaFqRMWFoB', 'tz1UhrM1GQ3tPrJjoJWBa1CApi25h4Vgj89U', 'tz1WY7Bd57dsncqjRfnr8JirZ15jTsEXMcPJ', 'tz1MADhbJzT24FTmNCHrz6wG7sDFKMjmw556',
                                       'tz1KgvfkP3R6n7RRnD85gEa6E2YRj4u4q8aw', 'tz1crGwLeD2FLpATSyDv7wqmu95sE9s7ysVV', 'tz1QHcxZjviBKEuarT7txvPtWj6XaGGu52gK', 'tz1WL3g6oLb2DDNP9Zny3fXHqE7Caznh7sPj', 'tz1SftNcxaxKsToMLAnGvCgZSCQZMZ4vkAJ7', 'tz1Uk4bEsm8zfX3Q83b5JPwNe4pGXvZsLUKA',
                                       'tz1gDU8NdB5moFYc9nCUJBkjgRfxCP5Y6yiT', 'tz1TNhL9NmX3fc8Yuqs56ayxrWhWkbWjCoso', 'tz1WqT5wwKqi5VSkPfuR771rNbDwh5igxoEp', 'tz1bp6ptQh5DZCJKyqyfjwn87PoDQbRRTDXy']
        config['public_keys'] = ['unencrypted:edpktuDbNDnahwZ3LP6wq61QWYzK2E2LTwTZkQdTn2Hjft24ip1vsi', 'unencrypted:edpkvZLd1uNJPDrtGr6QPv8vsbnptxR8eU4q6Mu4fqHmxsYEqXobT9', 'unencrypted:edpku2fYWBsVfxNuBx9R5ac9X6PTTbrDHbUPLoAXnbWPF7RKPJ6ske',
                                 'unencrypted:edpkurUb9bJfBBz3PnfdhXs2vcQoUR5dgwjB9K88wnm2gpQ8aMnwQs', 'unencrypted:edpkv2mgr7kMVwKsL84EQkciFnNuxWmfhF35eZyfjpK2kWDdidhzhZ', 'unencrypted:edpkvBACLdhPD6BpdQdQMQALr2kqJAUXk9hgoxEkUoADsKDT48Vwir',
                                 'unencrypted:edpkvZVQ2U8Vp7KgbJE6Kib7Fh7beMRwZp1dyrKPEccKj3JSJtnaQf', 'unencrypted:edpkuu8UPKm3sQeWz6uSsUwH69w4krXKbtgfhRDSfnBBdJyY2MujpP', 'unencrypted:edpkuoxi11sYWhR5Jq189ZV4yeiqT4SB8NVdrWqyE7ngDc1TdfsFzc',
                                 'unencrypted:edpkv3K4shxSSHQpUAqqYQ71f35XHA4H3ufQzxZKVBuG4DbwwZt277', 'unencrypted:edpkto65LqREtsyiMKg66BUatrKwQeWFuxqvW1sbcyZoSxSZs9MHD4', 'unencrypted:edpkto3bdTyATkaU8thVxc6YCUt1XeK64FhXALzXCXsgwWodKRiXYC',
                                 'unencrypted:edpkuDLzWGujak6t3cTSncouJmoJuLYvsgkZQptYY5CwAkXjtKd8CB', 'unencrypted:edpkuy3xEyTHbxQsB6XUo7MpbUBx6Bo92dkiwGG1uk2G2Xo6MQ8dhL', 'unencrypted:edpkv1eb67drSYYLjaMsEn6qsgtR2WnKUycdXRG8R7YpEYDa1YBdbg',
                                 'unencrypted:edpkvYi5fxuuEhKNZQB32ie2h77Ppjg6J8SeD7kKbDUuCPRha3eoJ1', 'unencrypted:edpktjYcsD1Fw85WgxXX6oKEU1h6HuFm8NjVbumgfJV7xK9UtrSyhR', 'unencrypted:edpkuQEqYtKuTyi6gTJr7n4kAY3STQ6RbciBSc5Ws6W8DejtkuPiYT',
                                 'unencrypted:edpku1GqQXBq1PNi7q1JifgNk5yz4jTMGBxhj5fBhCrAkXSdxMy7Fq', 'unencrypted:edpkunMPPsSqNz5KRRV6s5nnT4hpyT1n1dVcsAjXCn4LwgCNpmmo3W', 'unencrypted:edpku9ZuEH4LhMJhKm3CWxDdCjhEmL5ytK2qE1ys3fGVFXcMqc5Cgn',
                                 'unencrypted:edpkurBPBmpUZAa4bC4XSwiQjm2TA4HsykaS68de49oqckr1e9rapX', 'unencrypted:edpkuWsPrAEKdsTfFGsEWgyyBNcRG5qrfgxnVgBDvqCxtqstfWdQRf', 'unencrypted:edpkuXc4dymu1yEWbvj3NcHiizcDtZAeXb9wESmjF9ujV79QCsgLov',
                                 'unencrypted:edpkuW2e8YLeNdteaT3jreR1BZKkJVL1WCL4HVk98Sn463ajcvnQa8', 'unencrypted:edpku8QiFqko3kKpzSzGVy8B39Jbahxqx1HNEsCquwkyvJVpvgsHwV', 'unencrypted:edpkv6kTSNEQAfj8PVeS36KztpkkHGyQFf5y4heUZyD8ySa2BwSYhF',
                                 'unencrypted:edpkubH6xrUvZRh8EKH3ReqVuyJmkQLxVhLkiHtktzNVjh97Mk2koH', 'unencrypted:edpkvCdXzzvpXCvEuLqyMLDunjV5EKajhPvbsy7hsPdwAnqyV3EjL8', 'unencrypted:edpktgwn8ghsbNmEvrhHagEq6HyMMXfY9pi6iVca5qxSNrbAgniWhv',
                                 'unencrypted:edpkvWzj3K6Fd2wYBGeyCXMMvFusz9RBUVEVypfHisKWDKssdhgL9E', 'unencrypted:edpktu6FVJ8a4DG3Vz3PK1qvTYsWsk639cYNnCuimKqiZLCigMbX8P', 'unencrypted:edpkuUgXXjC8MemQgpzNnSDL9Y3w2QoCofAd2fV92vAfPwqVbnfTzA',
                                 'unencrypted:edpkuEGDDAriiqXUHtRkKGDFjK3pGKBKZGgmBen1UNzJvyCvMmGgPn', 'unencrypted:edpkv3T76H9XCy8Z4warJNpv9E36zvtJPBd67gc6yLjRSp77Nqzumw', 'unencrypted:edpkuiPk8H16D87DA8gpQhhf79BeLqwz8p6sRu6jExP8qofQdPik1k',
                                 'unencrypted:edpkvU394Yw1722eEVhgZLqVMpzBhZ9qepkqbcvxDKUocvJ7v4zX7e', 'unencrypted:edpkuMedxYchcHmKvgKaVUvhzoDZEfAzdqz9Tj4oLAwam8pWKhuhcR', 'unencrypted:edpkug2Bw2AcuKofRZ8Dd9KjDu3hNGWcBsj1L1K5uh6ia8pkps6Zyx',
                                 'unencrypted:edpkus9jJBpNLEVPtkX1UomoJ83zvxZAU68UBUBsheBGoA6zHCodGn', 'unencrypted:edpku64E4JkiEac6yo5ALP5uD7Q8wL1GhdRoWhi4pSmEPV6opcdLxB', 'unencrypted:edpkuhgGwomxT1UTRnGu6yzBBK54xeuodGkEUzU5eQ7hA61J9GpReX',
                                 'unencrypted:edpkuEHqwhNnCK8GwVkLok5ra9fTHGBvvC1XoutdYcRVeKSDvTDbTM', 'unencrypted:edpktnc73wVyifQ94PUVjw2H6yQKLMM8Su8nQDBhhwg6PaEP5ZBdzz', 'unencrypted:edpkuxZwkMdoneadyegdWbrCHdGM8CBNJbgikKy55eC6QcW8HfagUB',
                                 'unencrypted:edpkvaetDotrdDutFdaHCoHTWr3m7dXbzZHLMQ6gek9jVtsXwrJyaS', 'unencrypted:edpktv5G2QjsotfVgyWCm9tyMaHD5iqjtfCk5WW89oa5ryeWsXqRmi', 'unencrypted:edpktho9mAbYgN4CCffbDGQJTCfugpFh5a19V1oNnZdYCXqCa7piWx',
                                 'unencrypted:edpkvNuAx4B7hviZJRp1HvdLChU7mo3EaHH1qHvWg9hDQFJJQzERXm', 'unencrypted:edpkuGbF4tqBbBVdRyythUjJBw4RzFP2VdRJ9aRtmUjKS3irqWmBwZ', 'unencrypted:edpktgfdUjtH9aQHwszwE4MPTV2efnuQbFA6FYBFLaEcsVPXMEmHc6',
                                 'unencrypted:edpkuRoKYrqRG6wK7xzmUhakCUiobis7SZRn7Qqppv16BdjgTFg54s', 'unencrypted:edpkuDVPvzNBjDFSXLbmCREjvrWHrzq8sfvCuHeggSYiv6C4cznANK', 'unencrypted:edpkuAqJEeUktLj6BJ4JrNu7g7EwXaBUoCXY7gNHj7vCStAg1q62m4',
                                 'unencrypted:edpktriaooiTrRvsohWPaNBhfFguCgTkDx8SWhFUdKpx2RqsKYJRqe', 'unencrypted:edpktm9QG8DCq79MfnsaJxHLdSpSp7XejT8wdeKHHShSAXXCtWNUHa', 'unencrypted:edpkvJ92tuknDoyQYqx8q8bcWrc7TXeJxyquLZFr1RUpcRxyqQ6omT',
                                 'unencrypted:edpktquSpYGjXoVKDNQWD4hJwfos2sMqVZsZsSkjGUYTHnVmuddYuu', 'unencrypted:edpkv2czfXQVKL8bXSnmAWn3yhzFzbprLzLzhyTUPrZfe93N9xngNF', 'unencrypted:edpkuTLg5doQP6193h5RWfvvGuCa9d1osdJaATH7vz13r2wEykPxQD',
                                 'unencrypted:edpkuTQuXUiHhUmGLT7NUusEs9kiBfBSDiXnJ8JJHfHmozFBUKUxa1', 'unencrypted:edpku4hwSKuf8kFwmmecs3ZNWwCM6m2vWdhQyNEado57rMbZRMtrhK', 'unencrypted:edpkuJFCS52nrjghwQVy9wUzvTWSoU8Dmm9g38w2t4gMvPc1BeAEis',
                                 'unencrypted:edpku42XhWbiN6UpdsbcJpmFXybF5T5VXYZJj3j5WhutENvzuYAWAx', 'unencrypted:edpkvEMjGbJ55xMe7Y3jfKcXvzJpUScdtpeX2Ue9cMKebdVNhgrBM1', 'unencrypted:edpkuxFCPEiszpchSGiPuZiHWhm9i1S9HRgWyPAPJiKVCB57k2oKif',
                                 'unencrypted:edpktiHQTK45bhfpJHN7ZZSSuyAuLLXqTWpRru1RQNJMquPfTfjpU7', 'unencrypted:edpkuFUpXshq5wkFuRBvSGjeWDzE8nHxUQKCdc1gD6gP8WKGobz7qu', 'unencrypted:edpkvEvRHZ8vF2dQgrjiWqpUsWYG89TnA5KUFicH94mEHKRC8GRwSM',
                                 'unencrypted:edpkuFkPEaEjHhqjbfDeSohACDaZDTQdTEGsGhePsABdyofgGvXxp5', 'unencrypted:edpktomsUdGfuzpbDhM9M4ottzLxq82HDceu6X7iTJoz31ygcgjT6L', 'unencrypted:edpkuVgrKUEE2bMujPYZ1Svi199hTcoqYLNFZLZKfY9YdVjLHPCsty',
                                 'unencrypted:edpkvNfxD2y8XEsuMLFvx2z94ohYvsnbHrvPEHuZnvxKXKz7FrF4Ra', 'unencrypted:edpkuRKCbVt5ASuBdRZuQFUPcLyPcLtYdMvCjkXiGbzRGf12wrd3Bp', 'unencrypted:edpkuP71TTR9jggdfzeazLZYzMpsKw2BSYCcv3KDp8AJCytwnW66gz',
                                 'unencrypted:edpkuvCQXCG11dTGSub1MwuQSNJrzsoyEPWfgVMBo6hwzRUxcCWrwy', 'unencrypted:edpkukTn7L8PT9DQBvXvci6joWKjf2sjpKHAuy9zFujp3TUy3FBkZ4', 'unencrypted:edpktxc8bsprZAzaxLtWt8YgUqBBRbNJwYmymDFgdVUyPWqMNtAdjR',
                                 'unencrypted:edpku3LCh4H6VZ3zdT4F1CjQYASEM5QCWCf5wCY4pxmuqHUhD5CFJL', 'unencrypted:edpkuGjwzH67wVUD5m7WLp4AcXiaTps9n62moPR6WufBkb2FAFpq55', 'unencrypted:edpkuyYRV6yfsRkmrm21F3BYkeNFy9zyifroVGomSQobNUQU6qq91W',
                                 'unencrypted:edpkuEvTLw6HARyKSgUhiENg9MP2ueNb2mb9RuT1otC7cYKL8eb6W8', 'unencrypted:edpkvB3Z7sKhsP1UqTb5ZpMbhVeqyHyhW7iVgbiU7fWzfSkqvayUc8', 'unencrypted:edpkv4sw2XrDe1MNBA5rwMShJpzJ7wAgq4hTNnZqeDKgv99qLGF9Nt',
                                 'unencrypted:edpkvFF8Gs9z97zJ4uEsrZ6ciRBZHhdSAsjKD1NFhW9QbqseBbT8Mb', 'unencrypted:edpkuZsjwMANhxQgcktXCAySnvxdy9dShoD5HL7LQawq44T8r1xNdg', 'unencrypted:edpkufNQca9Jgmg98U4iPd4KvRbdZVTtU5G1dJMtQfodaUN4EMpb5j',
                                 'unencrypted:edpkuNnUph1M9heGUNsLcBWirAoAAzG1rVNSigS2y16GxxVkRRJ5Kq', 'unencrypted:edpkvVheYzmfFW5zuHxxn4urnSw5XYJx4qbSqrQLJpxesdjzLbjNSe', 'unencrypted:edpktrvEiVEWbpyUuu1LMnMWP5rnxq4s8g59V5iSE54zXytcFJPd68',
                                 'unencrypted:edpkuRZxDiuqYvYfc8ESaTdrhCLXSsxMNWFYu7LnCAfFJ1f4Wc5Duo', 'unencrypted:edpkuEPj4B9o6UM9ZRMNYUSRxHCc4Wtz8WLfeLXJ2as96oZ1y8UuaQ', 'unencrypted:edpkv78y3yn4h36shveeHLuVsRNvqRZ6pWJHjpKXnirHJd23uSabx9',
                                 'unencrypted:edpkuUTENQn9942WJ59sRqyHsGxkPTJvsLuQkTrrqY6YKfCHyD5MfC', 'unencrypted:edpkuC8CshszYtreLFURaRjtmsBL8cr6mAyZBorZigvWmFm9caobCi', 'unencrypted:edpkvakeymesxRThKMnKk2Csx5qbZprz28xKksQmrrG9Wdv6wqk7UQ',
                                 'unencrypted:edpkvGKwDT8S8kYEtFXmuiMgzvvWW1ynEXjcaJvgcuphQQsiNzZJUT', 'unencrypted:edpktua3ktZpVvjZKGVChYw714mCRkXahUaCZkp7fgGPzWtYCQ2oLz', 'unencrypted:edpkurFWpccsqUTQuenFMw9RktZWYYwVj18pFftXM9qTCnKMhLv7Qk',
                                 'unencrypted:edpktgkXm86o7LdjNEPXfq8B8PrgmqtZgTq61EVCAh82iMuy9Mojj4', 'unencrypted:edpkuwjZjfxfAJaudFYyrHCREWe2TnbxBtYx6q2Nh4LZ9uxbDe5UA3', 'unencrypted:edpkuTAkgBpz4dqWbr4fbsYePRfSdgyLs8anFKGGmUL2kmcuRmiSVQ',
                                 'unencrypted:edpkuAWTm9KBMbJMSm7NXhuzLmeYQ8boEWLuemdrwNjCrLgCA4qgDG', 'unencrypted:edpkuApNyqL4uoLfNRdoDgjR8v94psqyvybzTbSdYmeCF87kouTp1z', 'unencrypted:edpkuXPwWRc8qdM7WCFEULQobMiLQwLafWDDi1sGSibJS1fS8UDjTF',
                                 'unencrypted:edpktzpRpywbCFM3e5CUqrtYZYYUBH4P1m1NgGqcTRbG8MVVidGvtb', 'unencrypted:edpkuUDaVir2qM2sPA8H3rYVAdVkCc7vkmSsHwQfFz6CmtKmUhYJCK', 'unencrypted:edpkuaGfHSvdEkb6diKrFVaUHFkEXq72SmG1PcAumuN577tz6KWey9',
                                 'unencrypted:edpkvWKBGSqXpsgckvshq9t2XQS8h1xpU3mgQUgXCL5eq8Mq2A4oM3', 'unencrypted:edpkv97KcHETEnxEDua32Gn6HCRBjzyL9pBV9s5LB6dMqeUbZMe5hX', 'unencrypted:edpkuF6e323eWTfLYGUamN7d9ULwn7hAoD6ceczhDZg67YeYfQHSPm',
                                 'unencrypted:edpkvA4B5aW6bsqqufLvTQnYvV8KLG5Ac8VSvfv96YsbfPDwS8iQey', 'unencrypted:edpkuqb6XTnf7xqY2qJsQPaabHKyCsMV5zzfHJ4Q6BWzghz8SFCFau', 'unencrypted:edpkv9XsEPjxWs1yd3wTEctD1QTgNCzvyHmhEoNU9D6XVEzJqQ62nw',
                                 'unencrypted:edpkuX42YgCRhHvzixsdcacg6DygyKiGkk8hKpzi5upeULUKaVfrBi', 'unencrypted:edpkvBVgWt1zqfVcc6s1XxdGWuxXi779jrCKfD9yE7RdmHdVazhC7x', 'unencrypted:edpkuSciyfagn4f5bd6WMcQS3JCJ5hPNT3vJ6bk8HJbjFGhu21YJd5',
                                 'unencrypted:edpkukSguEt3FjDWCTWqmcHP7JiUK8j2cm4YCDxqSAqXJEqjRmaE8X', 'unencrypted:edpkvPfNUa29qCTmYDuZV6AUBBo6GW6tpS3uKkGEiQViuRuojzB5Ls', 'unencrypted:edpku7uacfXhNj3EoUGryPNdmRNHezd1RAHzFs3hmu38TcvDQYAa9m',
                                 'unencrypted:edpkuez1LraviswmVJjphxApvgH4LzFJy2C9z2ATG1vk8v6eoi99ma', 'unencrypted:edpkuorri5KqWCTJCU1Tvb4SRpqxhsaBkG5WZRc4LA5FmgiLDrArBA', 'unencrypted:edpkuyfXXZqbTswDH8hFQTzVryMYbSvMY9nNgRccB1HaL7jafbWxcq',
                                 'unencrypted:edpkv4ccuPwjHFe9YXcymJGyTM4F6TeRRZkcifrvCSav2gcV6oRZmX', 'unencrypted:edpkun6gRRyEg2jvcx3PKErkoG858VE1rHj6zTabmit3uoq3schyvp', 'unencrypted:edpkupb1wrHPvjjhgcjMaj7Poq8oAsGSpPRBEH2psGoEMkmbTJcHah',
                                 'unencrypted:edpkuHGgpUA5joQ64me5h93Bktd84yGMQviXeXo7kDXPpXexRJm1tf', 'unencrypted:edpkvFjNeYFQYZTNVV3osx7h3QNvspskBq4Aiq7LhuJ6iU8BxruHSg', 'unencrypted:edpktzRPgg4KmCKbtDLLWRN1PsHqyKVbusZ5PDScbEhhHtWmSc5PD3',
                                 'unencrypted:edpkuki46W2PSeBMiWmLbbM8BonjBK7xX69aS8nbZJUrw3TdoTDsUc', 'unencrypted:edpkv2twCEtC7EvAYo9VWYPnj3tuBxBd4My3sbwqKv7wPv6LAatLtZ', 'unencrypted:edpkvAKo9ALkwcXQga8BatbpbsFpS2hLFYs5KZzt8ScQqdxyvBzz5b',
                                 'unencrypted:edpkuRxwtLbRALdBVamqzd961fRbeTwzVu5CjrniWDUgTgQf9Vzs2F', 'unencrypted:edpkuWHMyuzitrZeDF8ZqQt3zVZhxbodhVdHtRY9Bs4D94tsZhPcYr', 'unencrypted:edpkv9QPA1uPvkjgJd1qZQmYMRN2uMZ8ov6BZUQ6eDAkVWHGvWTewd',
                                 'unencrypted:edpku6V3NzgdjqoGKQ84Cp1B2ymHe2qAfn4iuGM1KHTSE12LmV739v', 'unencrypted:edpkufJc8AwTfdU9QRQTEPBT8GWXenmxCaRuJdXts5rmB48krwthiH', 'unencrypted:edpkvX2Hhiz4WykyyB5r8qSrbBsHnqFB46eJBQV8cEELynJXfB9B7i',
                                 'unencrypted:edpkv3BAvMVdY8wZfQwomnxqHyAqoY4FHKWg9kn1s4GYzRi9tycDyk', 'unencrypted:edpkv32gVt7cvHCbp62mQXe9dPjXYbUfnNVafrwR5LcxaeuvpS51P6', 'unencrypted:edpku4t7Y5YjzuP54asP1fQ4aqLnx3nABTB52GbpLzHf2fU9wKLqUh',
                                 'unencrypted:edpkvD1VXH7nRhnDLgvKDc4PXyCEbh25wvwXLQTK7YWJrJUteYboou', 'unencrypted:edpkv7ANwUxbSwbEALoWcFhnikKMLLAQ4GEBNH9e5zPFEpkCEyrmYP', 'unencrypted:edpkuBFcfpkukDZpLitb93H9u5onpN9jsQwT6hJTMNfPfwresKgAKM',
                                 'unencrypted:edpktipAKTDKsA9XfL168mf86q2uZHqQHZMnoSzCV1mC9M2NcKK5XG', 'unencrypted:edpktkV7fjjd35xMMVp7RD5LkvyAepu7ryvpfe5njNYioZmdANmV4k', 'unencrypted:edpku9p7xHhn9hUnGDmHMfgcBzs7VpenZC5MmE9wcAraoVN7L87UoR',
                                 'unencrypted:edpkuQah8TrtLX85ttvbNHfrU4yq3hrB9VCmW7QVRcQQvZ9yZYG5s6', 'unencrypted:edpkuHyG4T2WQgB6RJafDtWDayfsWLVqv8z3CXqa1vc5PEVwHaFhxM', 'unencrypted:edpkuu2hmvTin7g5eEtwdqKJSkVowxVtCBjtBbgpJKR1Mc9zPCBmBx',
                                 'unencrypted:edpkuaMejqUzfQEfoxg4aaALrtVHzE2dZeZxMGtE9fqBGq7tUvGRst', 'unencrypted:edpkticqftcUBNFVSv3KakUKVANtmc8tbpeaqxjtk6xkfHBTkuS6Mm', 'unencrypted:edpktrRPGeWSNiZmbiAJqmf8bZcTcKn6aAThpBoCVrAcYL5Zcy5gmp',
                                 'unencrypted:edpkuhuf1ZaYQwWdUxtkskrSmZJQfn7ZZq7w6Cyhxmaz3Ty6zYe4Xa', 'unencrypted:edpkuc6zwfVAJuEgvEuZ8UQDRTh5yzo7rkZBSa4g4CGnTNKQhuLXkT', 'unencrypted:edpkvYMDpzWH6CcMGCQahuwsojCtHL1QshS8h2LbkAr5yJThRBdz9a',
                                 'unencrypted:edpkupEvc3UnvLRhdAKg8LzaGffA5B7Kvd59i4ZnwNdVHziYYs8APo', 'unencrypted:edpkuusecsh8jJ86nx8c3nBFNrgsMd9j4uhpfX4ky3xDsvN9vtBDzT', 'unencrypted:edpktkNQ9vxwHZzCL8gjETPJMoD8wGZhT1qCK6hsu7pZCjvQbqGQpg',
                                 'unencrypted:edpkucuvusXQkXpHDGNgWGfBoPTbzMBUbc8XDZtog7YHi7bBGKdfho', 'unencrypted:edpkvBuVgGhz47q547mykYncw8gYsLtnQtbdZMWLEPQ1LsmiXJt74o', 'unencrypted:edpkuV2gpGoeZs2LnfUJatSTvfuBAsEZwkuJnCCzqxjBBgiSn95yrh',
                                 'unencrypted:edpktnAcxoYX2QRTKFjF66qYMBWXMDh6Ut43eSnRCUkmjcMJmfCtgq', 'unencrypted:edpkuDzt9sxFYheZFjkagADnADQDK8nY5MQ25PV8EWNMSHJyhhe8DC', 'unencrypted:edpkuqyVo2kPLLNCxWWptmV8pjiwHcdRpPk9ReCTG2tfcTLqtv79qq',
                                 'unencrypted:edpkvVfjZE4vRN3K6g4Sa4PuY2XFjqkHyjLvoQdjd9sK1PckwyZLvq', 'unencrypted:edpkvNFiYpUfpEexxkxH3zX85mEFawP7ShyBvNZJY6cVdoWekWi3v2', 'unencrypted:edpkvCrN4wVkfduByPrjS9BLA7NNyjavHha4v15ge7PzSemyY76Rvg',
                                 'unencrypted:edpkuUKijj85HdnMVhvpFApJ9X9u7qU8cRzeTN8qq3hWB1kjWn7aVa', 'unencrypted:edpkuP4PU1m8UfRDDZnSSBE4RprzJjDvaop9GCue2kcxBT2nYkjQm2', 'unencrypted:edpkuPY1BjBDeBnj2n2Afk1aYmW1XWrQULP1XZf5zTjM4yR8SnkLf2',
                                 'unencrypted:edpku3UEefvmDU8a39cSST6bMAhPXLJHsHTHPLFXD6JmknZVhXQiQu', 'unencrypted:edpkvQ51cbkV6HjqqMJZd9sRTQMmMDk1ayza7YpQjCAXMc2bj9BhrU', 'unencrypted:edpktwobLLcZq9goiLWrNmwKELPiNXiUb45dnzVWN2rRrVg5SzuKAj',
                                 'unencrypted:edpkvAzF92RtmGaAP3Vc5NNWo5VvH1XXAgdF63rJEGzoGYaksFv6KU', 'unencrypted:edpkvPWBjGT1QaVmnrp4e2UWdFesV2K3X7oaZgVmiJHAmcPBt2Jsyp', 'unencrypted:edpkvK8QPu3f25AadKuuq4uuF1ngH9aJa45abjjM5YxX83QALkcC4P',
                                 'unencrypted:edpkuaoiV5prCx9oD8XHF75E3DVSCqZY8WE92zAXt4aGf4QeartjBU', 'unencrypted:edpkvFRh5XW92oS5EjHTKxA1QHJSFByorYkJCvmyLBeJzxiHycFMmw', 'unencrypted:edpkuCJym8KK7BKnVo94zSu6iwQoSHFe3DkU4HwUQVvQgjvZA971RT',
                                 'unencrypted:edpkurBVEQKo2aKSqGrNkkToGxJJyD3ydpuBHcqBWPan6A2eQG3mP4', 'unencrypted:edpkubHS5VhiVPmHXyws9nUXxh5uapvJSqx938Z9jbdse8TdDaK9iH', 'unencrypted:edpkuU16g8xSWze1jpaD3m9q7aPjadcNViKDhCgSX3ha4AEur1TJfo',
                                 'unencrypted:edpkurq4WYdcerU1tW8DNA5FQzqg3YjF91TzcvuGcjBQdXYvu2tiT6', 'unencrypted:edpkv9CqFP4ioYBYJaNs1PsAgjvbP9hp8PxeQGpuY75vgwCRYvnyd4', 'unencrypted:edpktw2RPVPzoge7JUME7u1xjJTVMBxWTZEhg3zSEp81WjF4DxuY12',
                                 'unencrypted:edpktjPJ3Rb5GU4ehmh6kPjhuUeCi1o1ZiWvvNXU4qx37VgZ2AQzB4', 'unencrypted:edpkv6guNTx9nbVCKbu5xs4z4KYCZYHEakSVa5mY9t9pDpmshW941f', 'unencrypted:edpkv4u98bofjJC2Fx3FQ6AnD9RjP2nW4ndLNBHZGgKicmynXXgifM',
                                 'unencrypted:edpkv3Yuznk36Kg29zpTExFv8BjTGQks8XLsJfA17w56eU9RBsXdqT', 'unencrypted:edpkvJfeHNRQ1DdMapeDez4wmbn767vYoikoBN4iQQH92FcPm9wzHK', 'unencrypted:edpkvAqb8V7ykjdYtaL5xe89d33q1aEqgbkThBEzXVCvGZgz43jp1u',
                                 'unencrypted:edpkvAFJj1x24Y59HKgfdKTxhtwzbXh6td9xGVoF7m1w2tE6bchC4q', 'unencrypted:edpkupqPc4vjGhU75BnGfEuAtNKw1dZRK332TyNzbP3ehKyNXM4PER', 'unencrypted:edpkuUAz56PHYx1ixKRKXRWAYKjkfXNi6DPvSUXdfUKCdwiwes7WdK',
                                 'unencrypted:edpktjPRZKU6DhB4nMumiZvDUUgENmfm71GaN8p6KKTqmjy8zwDbME', 'unencrypted:edpkvaojVGKkG614zyAva2cDfUDNrLLTnJi4XKuw377Kp38M8iT4Uv', 'unencrypted:edpkuFBtCADhdEw85WYfiuE3nZ5DxH6886HivzShmXuEBb1fa3XnQE',
                                 'unencrypted:edpkuq5yubvEkugLMxSrdaWPvbKzLdUsq5RQfSbuQs1k6r5h7t5pYh', 'unencrypted:edpkuzta11FKHD6wRBbF84x2ZpvfP3H21LyvUXnbJWi4xTWfxxD6uD', 'unencrypted:edpkupiMLzUgdBgLD91t5sAi2G64Sju1Yq4Apfa6tr8duAqc92P7JU',
                                 'unencrypted:edpkv5VSHrAPwJhLJ5gcqGaBB2H6KZ9bAKJtEcti1q6XnUYXFPNuu9', 'unencrypted:edpkv7q9kKSkbghidcgZZW6mBeNJPbHcSEjFmBXdMAX5pEBaJC5XuA', 'unencrypted:edpktnEAqUpziDAQeUwLzDj57cRKFHMRWzs8y6ecNxbaU8VoVnHpA3',
                                 'unencrypted:edpkuogsN8oBGqu4UkBTtSYLf9dKpnHkYTXie73hQjkvnFPjPT68FZ', 'unencrypted:edpkuiansbB75uVGES41nSY9PxT4vQhB4tSbEe9u6gWrYYwmNNPD91', 'unencrypted:edpkv6DGHic1wbZfiWnzw2Gg2RQ9EENvMTtsTpEFbkPxnbRWKqh8er',
                                 'unencrypted:edpkuMnHifnEvLamtoKjGYxweBu128k6XtMa5aez9Ek1cCwM54VJib', 'unencrypted:edpkvGFvxvGj7DBd3qisBvR1TT7Gj9pAhKM1QUkw1uUUyGtvQroDkV', 'unencrypted:edpkvDTZr7EezZX99Y7Jsfh14qRHGcE1uASy3wfhHX2h6nNL76XKEt',
                                 'unencrypted:edpkudXNcFXwD9shccmNdC6UebGCa1FkiHb6dh8oXjCEacgLR1PFep', 'unencrypted:edpkvGcLKUu6c1FRXgYZxA4HnywLgJPUCMPz1hpKLRMinnpNCrE4UW', 'unencrypted:edpkuesNdwX9CSkecNVkETXo3QGiUPJSk611FSM8jaHmE7uzSpCBaa',
                                 'unencrypted:edpkvLjAwyPc78rWmQ4sAJCGqX8iEciFgoachTbtxADDmLAhjohmaG', 'unencrypted:edpkuNh36KUVFv1b6XSdJpR7VtfwHXBJcwKz75vFeE6Fpvqi8hqaQm', 'unencrypted:edpkuUFYHWXZ9A5hjGrefo7X5LKaXVGYUm9CvUENycBicKx9Tx9SJ9',
                                 'unencrypted:edpkuoWX3WgD7NDSeGadQbcYf3aCrvEvzeD7kx2Y3UX4aCxATiJWGy', 'unencrypted:edpktrZVXbTfeh4FTKHhCwSv3GoethsXmVrqKxWDPYbFbAsDchbVa6', 'unencrypted:edpkteZYTjCBkfd5UHPvuDxmEwRWjjhi2pQzNFwy7YL4JMbbVwMmTA',
                                 'unencrypted:edpktxZjkGpiCtEDubxrRczKK2iXRz1P622xGnFWcf9TtfJzR6KDB2', 'unencrypted:edpktqetG7NXamTrXJibaPbVGZc5iHvUdCqgggEVN7Dh1doig5DgDU', 'unencrypted:edpkvPCZtriCCHcAxK4NcVo6ntmoxJH5UcuzkoT97Ex8bbcaA5oBbT',
                                 'unencrypted:edpkvP3s3U196uDfd3vWgM74x6CduQVVPyPD2zdbHpE61fS3DykvwH', 'unencrypted:edpkvHPfsZTr4nhtJ1SbWk6MkBCSpPUt8pviYANKbteq6hhYUo4Yyd', 'unencrypted:edpkuGq8jqoW5MG7AFftmorETyrFH795X3XMz4akJKxCeoiWPFe9Ze',
                                 'unencrypted:edpkubUBdfzTQ6UVUAoYSQyC4q2w6XRnfAikt6AxYb5Emd9vzrTLHC', 'unencrypted:edpkv4FnGyWgjoHWYjZezUHazKT8o4sBE7oFrBzk9JqhRcKjE1krP4', 'unencrypted:edpkuTETLh6H93VU4AarhSscYhqv5LPS4PpgxKSHz66MvcaH9Zn9BH',
                                 'unencrypted:edpkvYdFADMakhfnLJMvZ1VGHvKceXjjw4QsAXi415CWdBfxCPY84C', 'unencrypted:edpkuQyC176CAse6T3NkxPfVYDGo1ip68vHMjCwGFuokcvQ4b5hpE5', 'unencrypted:edpkvNuzkmSMXMNFWd7pAZDh8iWSk7RLFX7MFxrEPCjXdFosqy3YBJ',
                                 'unencrypted:edpkuAuyaKRsopbJSn7UonPh2YXpe4qkGx48bASMW8zU7gYqA6xoZc', 'unencrypted:edpkuyNshqbURJhnTJRP8xBZMthqYMpLQ8uNHAWZ5JW6SzQUcuBuAL', 'unencrypted:edpkukctMFCt8ov1sLMCWkxoBrapsaXPCuZwXt792SveTLwUtMw5X4',
                                 'unencrypted:edpku4n8BgxW8GzkRVMUJCpGqXbBQuU5xj46ZNWzv57EFGMpFGDCes', 'unencrypted:edpktjTuyNQuc9huZ6zP98J6bLyttWmA4To2F4rvkaSp4qhbBi3wJY', 'unencrypted:edpkvF56gQRw7ajQo1TLjPDQUygRT8o5kv6vKijKy6iQE1uwbnfcMr',
                                 'unencrypted:edpku7mLuuSCaNpZ2KANPkXiByHe4EXR9i6ib2PQqyUhYyapzpuQg8', 'unencrypted:edpktx1eSmi9XUcXcojM9annT8g7n9vVDqi13JPQutsqzj7E9hpSF3', 'unencrypted:edpkus8EHbGPBeXsRkEPfN48cW15SYLYUcKoEdqGSk9uLq4aSK2Lbn',
                                 'unencrypted:edpktjzpj35MuHXRm3t7dp2mNhGNydB8ni3YKqdji8cy8u7JGhATuX', 'unencrypted:edpku4U4XsXQMNf3fLrMfsW8eAjVyRa4J4qPDyCRCtF8rheymndkMC', 'unencrypted:edpku2iAVaGeSNcpfVEbeGNx6SQuPkWAd6tTGYUV4Zy4MpK6h8sJov',
                                 'unencrypted:edpktub7e7zCoT97aA7KAzrq96ZZi9msSJ1aVjHXz2yK6ZrHpJPEdT', 'unencrypted:edpkuMxF4EBitcYM9fyXZYTKRpJBhjtDMHh1Lz8GnbrizT25RsCSRr', 'unencrypted:edpktkC8C3ft8EBFQzVZSfG87pKje3PE1ZCZuwXmYqomj9eUkRfb4a',
                                 'unencrypted:edpktq7nRAUi7V91u9mKAeinaccys23tfFY3vSa58V2zNUeHY3kdse', 'unencrypted:edpkvDkM8dPCdTVxtjgumwVmAcz8PN94bbyJafvJ4Sp2zFFoLnM2ha', 'unencrypted:edpkv6FPBwcdeFx7LTXqRr9WEE6zxWzWmzmrDC6xN9gTsiwKLc8srE',
                                 'unencrypted:edpku6DyACWraANoPMghAYpJDK11DA19TjendmVbqH5GceU5eHMk2B', 'unencrypted:edpkuFsz35na5xrQccRRCyLPGV4n8zeHwx2b2Tj9bELkz5p527NwUE', 'unencrypted:edpkvJNzSs9MZYseDFaRbDk6qqZvEDYvXfiTD15XTBoBHAYrMJ5SHq',
                                 'unencrypted:edpktn2jCMEcQMzAgxzodaAKM5c2Cs5usXu4Y2JhmB8KGmAcrdko5a', 'unencrypted:edpku3P5Nb3UAJf7ueGKUvoV9rz7HxqBj24o7rVJXKirmP8T4DeEt2', 'unencrypted:edpktfex4E8x4shcFVsN6g8n5tAb5V3PNomnySVMbE4TzZgiMRAi5w',
                                 'unencrypted:edpkuxFAZoQdTh2cJsb6pZvELyG9adPiLYB5xjrnBEY58fhsod7G7z']

        Tezos.write_sandbox(config)

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].put(f"{config['exp_dir']}/setup/sandbox-parameters.json", "/home/ubuntu/tezos")

        peers_string = Tezos.write_peers_string(config)
        for index, _ in enumerate(config['priv_ips']):
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"~/tezos/tezos-node config init --data-dir ~/test --connections {len(config['priv_ips'])} --expected-pow 0 --rpc-addr {config['priv_ips'][index]}:18730 --net-addr {config['priv_ips'][index]}:19730 {peers_string}")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

        channel = ssh_clients[0].get_transport().open_session()
        channel.exec_command("~/tezos/tezos-node run --data-dir ~/test --sandbox=/home/ubuntu/genesis_pubkey.json >> ~/node.log 2>&1")

        time.sleep(30)

        for index in [0]:
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"~/bootstrap.sh {config['priv_ips'][index]}")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            stdin, stdout, stderr = ssh_clients[index].exec_command("pidof tezos-node")
            out = stdout.readlines()
            logger.debug(out)
            logger.debug(stderr.readlines())

            pid = out[0].replace("\n", "")
            stdin, stdout, stderr = ssh_clients[index].exec_command(f"kill -15 {pid} && mv ~/node.log ~/node_inject.log")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

        time.sleep(30)

        for index, _ in enumerate(config['priv_ips']):
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command("screen -dmS node ~/tezos/tezos-node run --data-dir ~/test")

        time.sleep(30)

        for index, _ in enumerate(config['priv_ips']):

            stdin, stdout, stderr = ssh_clients[index].exec_command(
                f"~/tezos/tezos-client --addr {config['priv_ips'][index]} --port 18730 import secret key this_node {config['private_keys'][index]} && ~/tezos/tezos-client --addr {config['priv_ips'][index]} --port 18730 register key this_node as delegate")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            if index == 0:
                time.sleep(30)

            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"screen -dmS baker ~/tezos/tezos-baker-004-Pt24m4xi --addr {config['priv_ips'][index]} --port 18730 run with local node /home/ubuntu/test this_node")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"screen -dmS accuser ~/tezos/tezos-accuser-004-Pt24m4xi --addr {config['priv_ips'][index]} --port 18730 run")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"screen -dmS endorser ~/tezos/tezos-endorser-004-Pt24m4xi --addr {config['priv_ips'][index]} --port 18730 run this_node")

        for index, _ in enumerate(config['priv_ips']):
            scp_clients[index].put(f"{dir_name}/setup", "/home/ubuntu", recursive=True)

            logger.info("Installing npm packages")
            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(cd setup && . ~/.profile && npm install >> /home/ubuntu/setup/install.log && echo Success >> /home/ubuntu/setup/install.log)")

        status_flags = wait_till_done(config, ssh_clients, config['ips'], 180, 10, "/home/ubuntu/setup/install.log", "Success", 30, logger)
        if False in status_flags:
            raise Exception("Installation failed")

        for index, ip in enumerate(config['priv_ips']):
            logger.info("fStarting the server on {ip}")
            stdin, stdout, stderr = ssh_clients[index].exec_command("echo '{\n    \"ip\": \"" + f"{config['priv_ips'][index]}" + "\"\n}' >> ~/setup/config.json")
            logger.debug(stdout.readlines())
            logger.debug(stderr.readlines())

            channel = ssh_clients[index].get_transport().open_session()
            channel.exec_command(f"(source /home/ubuntu/.profile && cd setup && node server.js >> /home/ubuntu/server.log)")
            logger.info(f"Server is now running on {ip}")

    @staticmethod
    def write_peers_string(config):
        peers_string = "--no-bootstrap-peers"

        for index, ip in enumerate(config['priv_ips']):
            peers_string = peers_string + f" --peer {config['priv_ips'][index]}:19730"

        peers_string = peers_string + " --private-mode"
        return peers_string

    @staticmethod
    def write_sandbox(config):
        sandbox_parameters = {}

        sandbox_parameters["bootstrap_accounts"] = []

        for index, _ in enumerate(config['priv_ips']):
            sandbox_parameters["bootstrap_accounts"].append([config["public_keys"][index].replace("unencrypted:", ""), "4000000000000"])

        """
        sandbox_parameters["preserved_cycles"] = 2
        sandbox_parameters["blocks_per_cycle"] = 8
        sandbox_parameters["blocks_per_commitment"] = 4
        sandbox_parameters["blocks_per_roll_snapshot"] = 4
        sandbox_parameters["blocks_per_voting_period"] = 64
        sandbox_parameters["time_between_blocks"] = ["1", "0"]
        sandbox_parameters["proof_of_work_threshold"] = "-1"
        sandbox_parameters["endorsers_per_block"] = min(32, int(np.floor(2/3*len(config['priv_ips']))))
        sandbox_parameters["hard_gas_limit_per_operation"] = "1040000"
        sandbox_parameters["hard_gas_limit_per_block"] = "10400000"
        sandbox_parameters["tokens_per_roll"] = "8000000000"
        sandbox_parameters["michelson_maximum_type_size"] = 1000
        sandbox_parameters["seed_nonce_revelation_tip"] = "125000"
        sandbox_parameters["origination_size"] = 257
        sandbox_parameters["block_security_deposit"] = "512000000"
        sandbox_parameters["endorsement_security_deposit"] = "64000000"
        sandbox_parameters["endorsement_reward"] = "2000000"
        sandbox_parameters["cost_per_byte"] = "1000"
        sandbox_parameters["hard_storage_limit_per_operation"] = "60000"
        sandbox_parameters["test_chain_duration"] = "1966080"
        """

        for key in config['tezos_settings']:
            sandbox_parameters[key] = config['tezos_settings'][key]

        with open(f"{config['exp_dir']}/setup/sandbox-parameters.json", 'w+') as outfile:
            json.dump(sandbox_parameters, outfile, default=datetimeconverter, indent=4)

    @staticmethod
    def restart(node_handler):
        """
        Runs the tezos specific restart script
        :return:
        """

        logger = node_handler.logger
        config = node_handler.config
        ssh_clients = node_handler.ssh_clients
        scp_clients = node_handler.scp_clients
