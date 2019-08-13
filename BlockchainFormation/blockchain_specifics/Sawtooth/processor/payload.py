from sawtooth_sdk.processor.exceptions import InvalidTransaction

class BenchmarkPayload:


    def __init__(self, payload):

        # First we need to decode the payload into the required fields
        try:
            # Payload is a csv utf-8 encoded string of the from method,argument_a,argument_b
            data = payload.decode().split(",")
        except ValueError:
            raise InvalidTransaction("Cannot understand format of encoded payload")

        # Now we can check if the provided values are valid entries for our transaction processor
        if len(data) < 2:
            raise InvalidTransaction('Payload does not contain enough fields')

        # Set payload fields with parsed provided information
        self._method = data[0]
        self._arg1 = data[1]
        if len(data) >= 3:
            self._arg2 = data[2]

        print("Created payload with {}".format(len(data)))

    # This function returns the deserialised payload
    @staticmethod
    def from_bytes(payload):
        return BenchmarkPayload(payload=payload)

    # Functions to access the data inside the payload object
    def method(self):
        return self._method

    def arg1(self):
        return self._arg1

    def arg2(self):
        return self._arg2
