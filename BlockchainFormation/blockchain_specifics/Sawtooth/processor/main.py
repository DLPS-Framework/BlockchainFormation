from sawtooth_sdk.processor.core import TransactionProcessor
from handler import BenchmarkHandler
from sawtooth_sdk.processor.log import init_console_logging
from sawtooth_sdk.processor.log import log_configuration

def main():

    # Set logging
    init_console_logging(verbose_level=1)

    # Create transaction processor class with specified address of the validator
    processor = TransactionProcessor(url='tcp://127.0.0.1:4004')

    # We have to instantiate our self implemented handler class which encodes the main part of the application's logic
    handler = BenchmarkHandler('benchmark')

    # Now we have to add our handler to the processor
    processor.add_handler(handler)

    # Start the processor
    print('starting processor')
    processor.start()


if __name__ == '__main__':
    main()
