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

import hashlib

from sawtooth_sdk.processor.exceptions import InternalError

# Generate the namespace for our transaction processor: 'benchmark' -> {9088e8}
namespace = hashlib.sha512('benchcontract'.encode("utf-8")).hexdigest()[0:6]

def _make_address(name):
    '''
    # Here we generate the addresses used to store and retreive data to and from the blockchain
    # NOTE: This defines the input and output fields of the transactions we send with our client
    # As we use 'benchcontract' as namespace input our addresses all start with 'dc7a45'
    # For name='benchcontract_result' --> dc7a45 + e54be707a312cf1cbd3ed406aa946f7b77ef39c84c077a8f4be9052158967e1a
    :param name: String which is hashed to generate the remainder of the address
    :return: address [String] hex encoded hash of namespace and name
    '''
    return namespace + hashlib.sha512(name.encode('utf-8')).hexdigest()[:64]

class BenchmarkState:
    TIMEOUT = 3

    def __init__(self, context):
        """
        Constructor

        :param context[sawtooth_sdk.processor.context.context): Access to validator state
                    from within the transaction processor.
        """

        self._context = context
        # TODO: What is that?
        self._address_cache = {}

    def delete_result(self):
        """
        Deletes the current result from the global state.

        Args:
        :param self:
        :return: nothing

        Raises:

        """

        result = self._load_result()

        del result

    def store_result(self, value):
        """
        Sets the current result to the given value
        :param self:
        :param value [int]: value to set as result
        :return:
        """

        address = _make_address('benchcontract_result')

        state_data = self._serialize(value)

        self._address_cache[address] = state_data

        self._context.set_state(
            {address: state_data},
            timeout=self.TIMEOUT)

    def _delete_result(self):
        address = _make_address('benchcontract_result')

        self._context.delete_state(
            [address],
            timeout=self.TIMEOUT)

    def _load_result(self):
        address = _make_address('benchcontract_result')

        if address in self._address_cache:
            if self._address_cache[address]:
                serialized_result = self._address_cache[address]
                result = self._deserialize(serialized_result)

        return result

    def _deserialize(self, data):
        """Take bytes stored in state and deserialize them into Python
        Game objects.
        Args:
            data (bytes): The UTF-8 encoded string stored in state.
        Returns:
            result [int]

    """
        try:
            result = data.decode()
            return int(result)
        except ValueError:
            raise InternalError("Failed to deserialize data")

    def _serialize(self, value):
       return str(value).encode()
