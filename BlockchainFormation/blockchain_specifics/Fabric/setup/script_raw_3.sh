

createChannel() {

    setGlobals 0 2
    peer channel create -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/channel.tx --outputBlock ./channel-artifacts/mychannel_genesis_block substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Channel creation failed"
    echo "===================== Channel \"$CHANNEL_NAME\" is created successfully ===================== "
    echo
}

updateAnchorPeers() {
    PEER=$1
    setGlobals $PEER $2
    peer channel update -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/${CORE_PEER_LOCALMSPID}anchors.tx substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Anchor peer update failed"
    echo "===================== Anchor peers for org \"$CORE_PEER_LOCALMSPID\" on \"$CHANNEL_NAME\" is updated successfully ===================== "
    echo
}

## Sometimes Join takes time hence RETRY atleast for 5 times
joinWithRetry () {
    peer channel join -b ./channel-artifacts/mychannel_genesis_block substitute_tls>&log.txt
    res=$?
    cat log.txt
    if [ $res -ne 0 -a $COUNTER -lt $MAX_RETRY ]; then
        COUNTER=` expr $COUNTER + 1`
        echo "PEER$1 failed to join the channel, Retry after 2 seconds"
        sleep 2
        joinWithRetry $1
    else
        COUNTER=1
    fi
    verifyResult $res "After $MAX_RETRY attempts, PEER$ch has failed to Join the Channel"
}

joinChannel () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        joinWithRetry $p $1
        echo "===================== PEER$p.org$1 joined on the channel \"$CHANNEL_NAME\" ===================== "
        echo
    done
}

installExampleChaincode () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        peer chaincode install -n mycc -v 1.0 -p github.com/hyperledger/fabric/examples/chaincode/chaincode_example02 substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Example chaincode installation on remote peer PEER$p.org$1 has Failed"
        echo "===================== Example chaincode successfully installed on remote peer PEER$p.org$1 ===================== "
        echo
    done
}


installBenchmarkingChaincode () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        peer chaincode install -l node -n benchmarking -v 1.0 -p /opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/benchmarking substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Benchmarking chaincode installation on remote peer PEER$p.org$1 has Failed"
        echo "===================== Benchmarking chaincode successfully installed on remote peer PEER$p.org$1 ===================== "
        echo
    done
}

instantiateExampleChaincode () {
    for p in 0; do
        setGlobals $p $1
        peer chaincode instantiate -o orderer1.example.com:7050 -C $CHANNEL_NAME -n mycc -v 1.0 -c '{"Args":["init","a","100","b","200"]}' -P "substitute_endorsement ('Org1MSP.member','Org2MSP.member')" substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Example chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' failed"
        echo "===================== Example chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
        echo
    done
}

instantiateBenchmarkingChaincode () {
    for p in 0; do
        setGlobals $p $1
        peer chaincode instantiate -o orderer1.example.com:7050 -C $CHANNEL_NAME -l node -n benchmarking -v 1.0 -c '{"Args":[]}' -P "substitute_endorsement ('Org1MSP.member','Org2MSP.member')" substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Benchmarking chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' failed"
        echo "===================== Benchmarking chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
        echo
    done
}

exampleChaincodeQuery () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        echo "===================== Querying example chaincode on PEER$p.org$1 on channel '$CHANNEL_NAME'... ===================== "
        local rc=1
        local starttime=$(date +%s)

        # continue to poll
        # we either get a successful response, or reach TIMEOUT
        while test "$(($(date +%s)-starttime))" -lt "$TIMEOUT" -a $rc -ne 0
        do
            sleep 2
            echo "Attempting to query example chaincode on PEER$p.org$1 ...$(($(date +%s)-starttime)) secs"
            peer chaincode query -C $CHANNEL_NAME -n mycc -c '{"Args":["query","a"]}' substitute_tls>&log.txt
            test $? -eq 0 && VALUE=$(cat log.txt | awk "/Query Result/ {print $NF}")
            test "$VALUE" = "$2" && let rc=0
        done
        echo
        cat log.txt
        if test $rc -eq 0 ; then
           echo "===================== Example chaincode query on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
        else
            echo "!!!!!!!!!!!!!!! Example chaincode query result on PEER$p.org$1 is INVALID !!!!!!!!!!!!!!!!"
            echo "================== ERROR !!! FAILED to execute End-2-End Scenario =================="
            echo
            exit 1

        echo
        echo
        echo
        fi
    done
}

benchmarkingChaincodeQuery () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        echo "===================== Querying benchmarking chaincode on PEER$p.org$1 on channel '$CHANNEL_NAME'... ===================== "
        local rc=1
        local starttime=$(date +%s)

        # continue to poll
        # we either get a successful response, or reach TIMEOUT
        while test "$(($(date +%s)-starttime))" -lt "$TIMEOUT" -a $rc -ne 0
        do
            sleep 2
            echo "Attempting to query benchmarking chaincode on PEER$p.org$1 ...$(($(date +%s)-starttime)) secs"
            # peer chaincode query -C $CHANNEL_NAME -n benchmarking -c '{Args":["doNothing"]}' >& log.txt
            # peer chaincode query -C $CHANNEL_NAME -n benchmarking -c '{Args:["writeData", "testkey", "testvalue"]}' >& log.txt
            peer chaincode query -C $CHANNEL_NAME -n benchmarking -c '{"Args":["matrixMultiplication","3"]}' substitute_tls>& log.txt
            # peer chaincode query -C $CHANNEL_NAME -n benchmarking -c {'Args:["readData", "testkey"]}' >& log.txt
            test $? -eq 0 && VALUE=$(cat log.txt | awk "/Query Result/ {print $NF}")
            test "$VALUE" = "$2" && let rc=0
        done
        echo
        cat log.txt
        if test $rc -eq 0 ; then
           echo "===================== Benchmarking chaincode query on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
        else
            echo "!!!!!!!!!!!!!!! Benchmarking chaincode query result on PEER$p.org$1 is INVALID !!!!!!!!!!!!!!!!"
            echo "================== ERROR !!! FAILED to execute End-2-End Scenario =================="
            echo
            exit 1
        echo
        echo
        echo
        fi
    done
}

chaincodeInvoke () {
    PEER=$1
    setGlobals $PEER
    # while "peer chaincode" command can get the orderer endpoint from the peer (if join was successful),
    # lets supply it directly as we know it using the "-o" option
    peer chaincode invoke -o orderer.example.com:7050 -C $CHANNEL_NAME -n mycc -c '{"Args":["invoke","a","b","10"]}' substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Invoke execution on PEER$PEER failed "
    echo "===================== Invoke transaction on PEER$PEER on channel '$CHANNEL_NAME' is successful ===================== "
    echo
}

## Create channel
echo "Creating channel..."
createChannel

## Join all the peers to the channel
echo "Having all peers join the channel..."
joinChannel 1
joinChannel 2

## Set the anchor peers for each org in the channel
echo "Updating anchor peers for org1..."
updateAnchorPeers 0 1
updateAnchorPeers 0 2

## Install chaincode on Peers
echo "Installing chaincode on peers..."
installBenchmarkingChaincode 1
installBenchmarkingChaincode 2

##Instantiate example and benchmarking chaincode on peer 0
echo "Instantiating example and benchmarking chaincode on peers..."
instantiateBenchmarkingChaincode 1

##Query example and benchmarking chaincode on all peers
echo "Querying example and benchmarking chaincode on all peers"
# exampleChaincodeQuery 1
# exampleChaincodeQuery 2
benchmarkingChaincodeQuery 1
benchmarkingChaincodeQuery 2

# #Invoke chaincode on Peer0/Org1
# echo "Sending invoke transaction on org1/peer0..."
# chaincodeInvoke 0

# #Query on chaincode on Peer1/Org1, check if the result is 90
# echo "Querying chaincode on org2/peer3..."
# chaincodeQuery 1 90

echo
echo

echo
echo " _____   _   _   ____   "
echo "| ____| | \ | | |  _ \  "
echo "|  _|   |  \| | | | | | "
echo "| |___  | |\  | | |_| | "
echo "|_____| |_| \_| |____/  "
echo

echo
echo
echo "========= All GOOD, BMHN execution completed =========== "

exit 0