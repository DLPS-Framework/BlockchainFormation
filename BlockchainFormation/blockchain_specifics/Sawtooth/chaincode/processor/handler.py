from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError
from payload import BenchmarkPayload
from state import BenchmarkState
import hashlib

import logging

LOGGER = logging.getLogger(__name__)

BM_NAMESPACE = hashlib.sha512('benchmark'.encode("utf-8")).hexdigest()[0:6]

def _make_benchmark_address(name):
    '''
    # Here we generate the addresses used to store and retreive data to and from the blockchain
    # NOTE: This defines the input and output fields of the transactions we send with our client
    # As we use 'benchmark' as namespace input our addresses all start with '9088e8'
    # For name='benchmark_result' --> 9088e8 + 3e049dd3e0791a8048c65c4c97919e8cd2d6faed745fe3093357079a3cc43dba
    :param name: String which is hashed to generate the remainder of the address
    :return: address [String] hex encoded hash of namespace and name
    '''
    return BM_NAMESPACE + \
           hashlib.sha512(name.encode('utf-8')).hexdigest()[:64]

class BenchmarkHandler(TransactionHandler):
    '''
    Class implementing the sawtooth transaction handler to encode all the logic of the benchmarking functionallity.
    '''

    def __init__(self, namespace_prefix):
        self._namespace_prefix = namespace_prefix

    # Name of our transaction processor family (uniquely identifies among all running transaction processors)
    # This name together with the version is used to assign transaction to a specific transaction processor
    @property
    def family_name(self):
        return 'benchmark'

    # Version of our transaction processor
    @property
    def family_versions(self):
        return ['1.0']

    # Defines the namespace used to store the state of the transaction processor on the ledger
    @property
    def namespaces(self):
        return [self._namespace_prefix]

    # Time out
    @property
    def timeout(self):
        return 3

    # TODO: implement state class to handle read and write to state then we don't need to pass the context
    def write_data(self, key, data, context):
        """
        Write specified data to ledger state under the address generated from key
        :param key: key under which the data is stored
        :param data: data to store
        :param context: sawtooth transaction processor context object
        :return:
        """
        address = _make_benchmark_address(key)
        data_encoded = data.encode()
        context.set_state(
            {address: data_encoded},
            timeout=self.timeout)
        print('Stored {} to state'.format(data))
        return

    def read_data(self, key, context):
        """
        Obtaines the data which is stored under the address generated from the specified key
        :param key: key under which data is stored
        :param context: a sawtooth transaction processor context object
        :return:
        """
        address = _make_benchmark_address(key)
        data = context.get_state(
            [address],
            timeout=self.timeout)
        print('Obtained {}: {}'.format(key, data))
        return data

    def multiply_matrix(self, n):
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

        print('Result of multiplication is {}'.format(m3))
        return m3


    def do_nothing(self):
        """
        Does actually nothing just to test the connection without any chaincode overhead
        :return:
        """
        return

    # The apply function performs the blockchain related tasks of our application
    def apply(self, transaction, context):
        print('Running Apply')

        header = transaction.header
        signer = header.signer_public_key

        # In payload we store all the information send to the tp from the client
        payload = BenchmarkPayload.from_bytes(transaction.payload)

        # To perform changes on the state we need the current state of the tp
        print('Obtaining current state')
        #state = BenchmarkState(context)

        # Logic of the application
        if payload.method() == 'writeData':
            print('Performing writeData benchmark')
            self.write_data(payload.arg1(), payload.arg2(), context)

        elif payload.method() == 'readData':
            print('Performing readData benchmark')
            self.read_data(payload.arg1(), context)

        elif payload.method() == 'multiplyMatrices':
            print('Performing matrix multiplication benchmark')
            self.multiply_matrix(int(payload.arg1()))

        elif payload.method() == 'doNothing':
            print('Performing do nothing benchmark')
            self.do_nothing()

        else:
            raise InvalidTransaction('Unhandled method: "{}"'.format(payload.method()))