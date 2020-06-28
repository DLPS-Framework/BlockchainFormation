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

from handler import BenchmarkHandler
from sawtooth_sdk.processor.core import TransactionProcessor
from sawtooth_sdk.processor.log import init_console_logging


def main():
    # Set logging
    init_console_logging(verbose_level=2)

    # Create transaction processor class with specified address of the validator
    processor = TransactionProcessor(url='tcp://127.0.0.1:4004')

    # We have to instantiate our self implemented handler class which encodes the main part of the application's logic
    handler = BenchmarkHandler('benchcontract')

    # Now we have to add our handler to the processor
    processor.add_handler(handler)

    # Start the processor
    print('starting benchcontract processor...')
    processor.start()


if __name__ == '__main__':
    main()
