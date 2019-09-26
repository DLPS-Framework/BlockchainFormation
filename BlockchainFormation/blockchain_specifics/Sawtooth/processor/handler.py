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

import hashlib
import logging

import cbor
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.handler import TransactionHandler
from state import BenchmarkState

LOGGER = logging.getLogger(__name__)

namespace = hashlib.sha512("benchcontract".encode("utf-8")).hexdigest()[0:6]

def _make_benchcontract_address(name):
    """
    # Here we generate the addresses used to store and retreive data to and from the blockchain
    # NOTE: This defines the input and output fields of the transactions we send with our client
    # As we use "benchcontract" as namespace input our addresses all start with "9088e8"
    # For name="benchmark_result" --> 9088e8 + 3e049dd3e0791a8048c65c4c97919e8cd2d6faed745fe3093357079a3cc43dba
    :param name: String which is hashed to generate the remainder of the address
    :return: address [String] hex encoded hash of namespace and name
    """

    print("name: {}".format(name))
    print("namespace: {}".format(namespace))
    return namespace + hashlib.sha512(name.encode("utf-8")).hexdigest()[0:64]

class BenchmarkHandler(TransactionHandler):
    """
    Class implementing the sawtooth transaction handler to encode all the logic of the benchmcontract functionallity.
    """

    def __init__(self, namespace_prefix):
        self._namespace_prefix = namespace_prefix

    # Name of our transaction processor family (uniquely identifies among all running transaction processors)
    # This name together with the version is used to assign transaction to a specific transaction processor
    @property
    def family_name(self):
        return "benchcontract"

    # Version of our transaction processor
    @property
    def family_versions(self):
        return ["1.0"]

    # Defines the namespace used to store the state of the transaction processor on the ledger
    @property
    def namespaces(self):
        return [self._namespace_prefix]

    # Time out
    @property
    def timeout(self):
        return 3

    # TODO: implement state class to handle read and write to state then we don"t need to pass the context
    def writeData(self, key, value, context):
        """
        Write specified data to ledger state under the address generated from key
        :param key: key under which the data is stored
        :param data: data to store
        :param context: sawtooth transaction processor context object
        :return:
        """
        print("key: {}".format(key))
        print("value: {}".format(value))

        address = _make_benchcontract_address(key)
        print("address: {}".format(address))
        value_encoded = value.encode()
        print("encoded value: {}".format(value_encoded))
        context.set_state(
            {address: value_encoded},
            timeout=self.timeout)
        print("Stored {} --> {} to state".format(key, value))
        return 0

    def readData(self, key, context):
        """
        Obtaines the data which is stored under the address generated from the specified key
        :param key: key under which data is stored
        :param context: a sawtooth transaction processor context object
        :return:
        """

        print("key: {}".format(key))
        address = _make_benchcontract_address(key)
        print("address: {}".format(address))
        data = context.get_state(
            [address],
            timeout=self.timeout)
        print("Obtained {} --> {} from state".format(key, data))
        return data

    def matrixMultiplication(self, n):
        """
        Creates to matrices of size nxn and multiplies them
        :param n: size of the squared matrices
        :return:
        """

        # Create one matrix
        f = 1
        m1 = []
        for x in range(n):
            row = []
            for y in range(n):
                row.append(f)
                f = f + 1
            m1.append(row)
        # The second matrix is equal to the first matrix
        m2 = m1
        print("m2: {}".format(m2))

        # Multiply matrices
        m3 = []
        for i in range(n):
            row = []
            for j in range(n):
                sum = 0
                for k in range(n):
                    sum = sum + m1[i][k] * m2[k][j]
                row.append(sum)
            m3.append(row)

        # add the entries
        for i in range(n):
            for j in range(n):
                sum = sum + m3[i][j]

        print("Result of multiplication is {}".format(sum))
        return sum


    def doNothing(self):
        """
        Does actually nothing just to test the connection without any contract overhead
        :return:
        """
        return 0

    def writeMuchData(self, start, end, context):
        """
        Writes a lot of integer key value pairs
        :return:
        """
        print("start: {}".format(start))
        print("end: {}".format(end))

        for i in range(start, end):

            key = "key" + i.toString()
            address = _make_benchcontract_address(key)
            print("address: {}".format(address))
            value = "val" + i.toString()
            value_encoded = value.encode()
            print("encoded value: {}".format(value_encoded))
            context.set_state({address: value_encoded}, timeout=self.timeout)
            print("Stored {} --> {} to state".format(key, value))
        return 0


    # The apply function performs the blockchain related tasks of our application
    def apply(self, transaction, context):
        print("Running Apply")
        print("context: {}".format(context))

        header = transaction.header
        signer = header.signer_public_key

        # In payload we store all the information sent to the tp from the client
        payload = cbor.loads(transaction.payload)
        print("read payload {}".format(payload))


        # To perform changes on the state we need the current state of the tp
        print("Obtaining current state")
        state = BenchmarkState(context)
        print("current state: {}".format(state))

        # Logic of the application
        if payload["method"] == "writeData":
            print("Performing writeData with args {} and {}".format(payload["key"], payload["value"]))
            result = self.writeData(payload["key"], payload["value"], context)
            print("Success")
            print("result: {}".format(result))

        elif payload["method"] == "readData":
            print("Performing readData with {}".format(payload["key"]))
            result = self.readData(payload["key"], context)
            print("Success")
            print("result: {}".format(result))

        elif payload["method"] == "matrixMultiplication":
            print("Performing matrixMultiplication with {}".format(int(payload["arg"])))
            result = self.matrixMultiplication(int(payload["arg"]))
            print("Success")
            print("result: {}".format(result))

        elif payload["method"] == "doNothing":
            print("Performing doNothing")
            result = self.doNothing()
            print("Success")
            print("result: {}".format(result))

        elif payload["method"] == "writeMuchData":
            print("Performing writeMuchData")
            result = self.writeMuchData(payload["start"], payload["end"])
            print("Success")
            print("result: {}".format(result))

        elif payload["method"] == "readMuchData":
            print("not yet implemented...")
            print("Performing readMuchData")
            result = self.readMuchData(payload["start"], payload["end"])
            print("Success")
            print("result: {}".format(result))

        else:
            raise InvalidTransaction("Unhandled method: {}".format(payload["method"]()))

        print("result: {}".format(result))
        # raise Exception("stop")
        return result