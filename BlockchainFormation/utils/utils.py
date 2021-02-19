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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.


import datetime
import logging
import time

import numpy as np
import paramiko


# File containing helper functions


def wait_till_done(config, ssh_clients, ips, total_time, delta, path, message, typical_time, logger,
                   func_part_one="tail -n 1", func_part_two=" "):
    """
    Waits until a job is done on all of the target VMs
    :param ssh_clients: ssh_clients for VMs on which something must be completed
    :param ips: ips for the VMs on which something must be completed (for logging only)
    :param total_time: maximum total waiting time in seconds
    :param delta: time between two successive attempts
    :param path: path of the file which is created at completion
    :param message: content of the file which is created at completion, if message equals False then no message is required
    :param typical_time: the time which it usually takes
    :param logger: the logger of the parent (calling) script
    :param func_part_one: String command called before the path
    :param func_part_two: String command called after the path

    :return: True if all files with the desired content were created, False otherwise
    """

    status_flags = np.zeros(len(ssh_clients), dtype=bool)
    timer = 0

    # TODO: Can this while loop be refactored to be more lean?

    while (False in status_flags and timer < total_time):
        time.sleep(delta)
        timer += delta
        logger.debug(f" --> Waited {timer} seconds so far, {total_time - timer} seconds left before abort"
                     f"(it usually takes less than {np.ceil(typical_time / 60)} minutes)")

        for index, ip in enumerate(ips):
            if (status_flags[index] == False):
                try:
                    client_sftp = ssh_clients[index].open_sftp()
                    client_sftp.stat(path)
                    if (message != False):

                        if path == False:
                            stdin, stdout, stderr = ssh_clients[index].exec_command(f"{func_part_one}")
                        else:
                            stdin, stdout, stderr = ssh_clients[index].exec_command(f"{func_part_one} {path} {func_part_two}")

                        # read line from stdout
                        stdout_line = stdout.readlines()[-1]
                        # logger.debug(f"Read {stdout_line}")

                        # Check if stdout equals the wanted message
                        if stdout_line == f"{message}\n":
                            status_flags[index] = True
                            # logger.debug(f"   --> ready on {ip}")
                            continue
                        else:
                            # logger.debug(f"   --> not yet ready on {ip}")
                            continue

                    # If there is no message we just need to check if path exists (client_sftp.stat(path))
                    status_flags[index] = True
                    # logger.debug(f"   --> ready on {ip}")

                # Try again if SSHException
                except paramiko.SSHException:
                    # logger.debug(f"File not yet available on {ip}")
                    try:
                        # logger.debug(f"    --> Reconnecting {ip}...")
                        ssh_key_priv = paramiko.RSAKey.from_private_key_file(config['priv_key_path'])
                        ssh_clients[index].connect(hostname=config['ips'][index], username=config['user'], pkey=ssh_key_priv)
                        # logger.debug(f"    --> {ip} reconnected")
                        try:
                            client_sftp = ssh_clients[index].open_sftp()
                            client_sftp.stat(path)
                            if (message != False):
                                stdin, stdout, stderr = ssh_clients[index].exec_command(f"tail -n 1 {path}")
                                if stdout.readlines()[0] == f"{message}\n":
                                    status_flags[index] = True
                                    # logger.debug(f"   --> ready on {ip}")
                                    continue
                                else:
                                    # logger.debug(f"   --> not yet ready on {ip}")
                                    continue

                            status_flags[index] = True
                            # logger.debug(f"   --> ready on {ip}")

                        except Exception as e:
                            # logger.exception(e)
                            # logger.debug(f"   --> still not yet ready on {ip}")
                            pass

                    except Exception as e:
                        # logger.exception(e)
                        # logger.debug("Reconnecting failed")
                        pass

                except Exception as e:
                    # logger.exception(e)
                    # logger.debug(f"   --> not yet ready on {ip}")
                    pass

        # logger.info(f" --> Ready on {len(np.where(status_flags == True)[0])} out of {len(ips)}")

    return status_flags


def datetimeconverter(o):
    """Converter to make datetime objects json dumpable"""
    if isinstance(o, datetime.datetime):
        return o.__str__()


def yes_or_no(question):
    reply = str(input(question + ' (y/n): ')).lower().strip()
    if reply[0] == 'y':
        return 1
    elif reply[0] == 'n':
        return 0
    else:
        return yes_or_no("Please Enter (y/n) ")


def wait_and_log(stdout, stderr):
    logger = logging.getLogger(__name__)
    try:
        out = stdout.readlines()
        err = stderr.readlines()

        logger.info(err)

        if err != ["\n"]:
            logger.debug("".join(out))
            logger.debug("".join(err))
    except Exception as e:
        logger.exception(e)


def unique(list1):
    # intilize a null list
    unique_list = []

    # traverse for all elements
    for x in list1:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)

    return unique_list