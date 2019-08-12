from hashlib import sha512
from sawtooth_sdk.protobuf.transaction_pb2 import TransactionHeader
from sawtooth_sdk.protobuf.transaction_pb2 import Transaction
from sawtooth_sdk.protobuf.batch_pb2 import BatchHeader
from sawtooth_sdk.protobuf.batch_pb2 import Batch
from sawtooth_sdk.protobuf.batch_pb2 import BatchList
import cbor

from sawtooth_signing import create_context
from sawtooth_signing import CryptoFactory

# Creating private key and signer
context = create_context('secp256k1')
private_key = context.new_random_private_key()
signer = CryptoFactory(context).new_signer(private_key)

print('Building payload')

# 1ST: Define payload
payload = "writeData,val1,400"

print("converting payload to bytes")
payload_bytes = bytes(payload, 'utf-8')

# payload_bytes = cbor.dumps(payload)
# For name='benchmark_result' --> 9088e8 + 3e049dd3e0791a8048c65c4c97919e8cd2d6faed745fe3093357079a3cc43dba

# TODO: compute inputs and outputs automatically in client analog to _makeBenchmarkAddress
print("building transaction header")
#  2ND: Create transaction header
txn_header_bytes = TransactionHeader(
    family_name='benchmark',
    family_version='1.0',
    inputs=['9088e8b43d9e8bf6ffd0d98ce885614954cc5969a0c7deddf645b036ea77d5805be5a7'],
    outputs=['9088e8b43d9e8bf6ffd0d98ce885614954cc5969a0c7deddf645b036ea77d5805be5a7'],
    signer_public_key=signer.get_public_key().as_hex(),
    batcher_public_key=signer.get_public_key().as_hex(),
    dependencies=[],
    payload_sha512=sha512(payload_bytes).hexdigest()
).SerializeToString()

# 3RD: Create Transaction
print("signing transaction")
signature = signer.sign(txn_header_bytes)

print("Building transaction")
txn = Transaction(
    header=txn_header_bytes,
    header_signature=signature,
    payload=payload_bytes
)

# Building the batch
# ------------------

# 1ST: Create BatchHeader
txns = [txn]

print("Create batch header")
batch_header_bytes = BatchHeader(
    signer_public_key=signer.get_public_key().as_hex(),
    transaction_ids=[txn.header_signature for txn in txns],
).SerializeToString()

# 2ND: Create batch
signature = signer.sign(batch_header_bytes)

print("Creating batch")
batch = Batch(
    header=batch_header_bytes,
    header_signature=signature,
    transactions=txns
)

# 3RD: Encode the Batch in a BatchList
print("Encoding batch")
batch_list_bytes = BatchList(batches=[batch]).SerializeToString()

# Submit batches to validator

import urllib.request
from urllib.error import HTTPError

print("Submitting batch")
try:
    request = urllib.request.Request(
        'http://10.3.2.75:8008/batches',
        batch_list_bytes,
        method='POST',
        headers={'Content-Type': 'application/octet-stream'})
    response = urllib.request.urlopen(request)

except HTTPError as e:
    response = e.file

print(response.read().decode('utf-8'))
print("Script ran until the very last line!")
