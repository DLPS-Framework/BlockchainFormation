#!/bin/bash

echo
echo "Build multi host network (BMHN) end-to-end test"
echo
CHANNEL_NAME="$1"
TIMEOUT="$2"
: ${CHANNEL_NAME:="mychannel"}
: ${TIMEOUT:="30"}
COUNTER=1
MAX_RETRY=10

echo "Channel name : "$CHANNEL_NAME

# verify the result of the end-to-end test
verifyResult () {
    if [ $1 -ne 0 ] ; then
        echo "!!!!!!!!!!!!!!! "$2" !!!!!!!!!!!!!!!!"
        echo "========= ERROR !!! FAILED to execute End-2-End Scenario ==========="
        echo
        exit 1
    fi
}