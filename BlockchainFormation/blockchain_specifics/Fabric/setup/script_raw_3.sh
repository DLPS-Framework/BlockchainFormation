

createChannel() {

    setGlobals 0 2
    peer channel create -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/channel.tx substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Channel creation failed"
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Channel \"$CHANNEL_NAME\" is created successfully ===================== "
    echo
}

updateAnchorPeers() {
    PEER=$1
    setGlobals $PEER $2
    peer channel update -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/${CORE_PEER_LOCALMSPID}anchors.tx substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Anchor peer update failed"
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Anchor peers for org \"$CORE_PEER_LOCALMSPID\" on \"$CHANNEL_NAME\" is updated successfully ===================== "
    echo
}

## Sometimes Join takes time hence RETRY atleast for 5 times
joinWithRetry () {
    peer channel join -b $CHANNEL_NAME.block substitute_tls>&log.txt
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
    verifyResult $res "After $MAX_RETRY attempts, PEER$1 has failed to Join the Channel"
}

joinChannel () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        joinWithRetry $p
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== PEER$p.org$1 joined on the channel \"$CHANNEL_NAME\" ===================== "
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
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Example chaincode successfully installed on remote peer PEER$p.org$1 ===================== "
        echo
    done
}


installBenchcontractChaincode () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        peer chaincode install -l node -n benchcontract -v 1.0 -p /opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/benchcontract substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Benchcontract chaincode installation on remote peer PEER$p.org$1 has Failed"
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode successfully installed on remote peer PEER$p.org$1 ===================== "
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
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Example chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
        echo
    done
}

instantiateBenchcontractChaincode () {
    for p in 0; do
        setGlobals $p $1
        peer chaincode instantiate -o orderer1.example.com:7050 -C $CHANNEL_NAME -l node -n benchcontract -v 1.0 -c '{"Args":["org.bench.benchcontract:instantiate"]}' -P "substitute_endorsement ('Org1MSP.member','Org2MSP.member')" substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Benchcontract chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' failed"
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode instantiation on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
        echo
    done
}

exampleChaincodeQuery () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Querying example chaincode on PEER$p.org$1 on channel '$CHANNEL_NAME'... ===================== "
        local rc=1
        local starttime=$(date +%s)

        # continue to poll
        # we either get a successful response, or reach TIMEOUT
        while test "$(($(date +%s)-starttime))" -lt "$TIMEOUT" -a $rc -ne 0
        do
            sleep 2
            echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Attempting to query example chaincode on PEER$p.org$1 ...$(($(date +%s)-starttime)) secs"
            peer chaincode query -C $CHANNEL_NAME -n mycc -c '{"Args":["query","a"]}' substitute_tls>&log.txt
            test $? -eq 0 && VALUE=$(cat log.txt | awk "/Query Result/ {print $NF}")
            test "$VALUE" = "$2" && let rc=0
        done
        echo
        cat log.txt
        if test $rc -eq 0 ; then
           echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Example chaincode query on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
           echo
        else
            echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')!!!!!!!!!!!!!!! Example chaincode query result on PEER$p.org$1 is INVALID !!!!!!!!!!!!!!!!"
            echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ================== ERROR !!! FAILED to execute End-2-End Scenario =================="
            echo
            exit 1

        echo
        echo
        echo
        fi
    done
}

benchcontractChaincodeQuery () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Querying benchcontract chaincode on PEER$p.org$1 on channel '$CHANNEL_NAME'... ===================== "
        local rc=1
        local starttime=$(date +%s)

        # continue to poll
        # we either get a successful response, or reach TIMEOUT
        while test "$(($(date +%s)-starttime))" -lt "$TIMEOUT" -a $rc -ne 0
        do
            sleep 2
            echo "Attempting to query benchcontract chaincode on PEER$p.org$1 ...$(($(date +%s)-starttime)) secs"
            # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args":["doNothing"]}' >& log.txt
            # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args:["writeData", "testkey", "testvalue"]}' >& log.txt
            peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{"Args":["matrixMultiplication","3"]}' substitute_tls>& log.txt
            # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c {'Args:["readData", "testkey"]}' >& log.txt
            test $? -eq 0 && VALUE=$(cat log.txt | awk "/Query Result/ {print $NF}")
            test "$VALUE" = "$2" && let rc=0
        done
        echo
        cat log.txt
        if test $rc -eq 0 ; then
           echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode query on PEER$p.org$1 on channel '$CHANNEL_NAME' was successful ===================== "
           echo
        else
            echo "!!!!!!!!!!!!!!! Benchcontract chaincode query result on PEER$p.org$1 is INVALID !!!!!!!!!!!!!!!!"
            echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ================== ERROR !!! FAILED to execute End-2-End Scenario =================="
            echo
            exit 1
        echo
        echo
        echo
        fi
    done
}

exampleChaincodeInvoke () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Invoking example chaincode on PEER$p.org$1 on channel '$CHANNEL_NAME'... ===================== "
    # while "peer chaincode" command can get the orderer endpoint from the peer (if join was successful),
    # lets supply it directly as we know it using the "-o" option
        peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n mycc -c '{"Args":["invoke","a","b","10"]}' substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Example chaincode invoke execution on PEER$p.org$1 failed "
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Example chaincode invoke transaction on PEER$p.org$1 on channel '$CHANNEL_NAME' is successful ===================== "
        echo
        sleep 2
    done
}

benchcontractChaincodeInvoke () {
    for p in substitute_enum_peers; do
        setGlobals $p $1
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Invoking benchcontract chaincode on PEER$p.org$1 on channel '$CHANNEL_NAME'... ===================== "
    # while "peer chaincode" command can get the orderer endpoint from the peer (if join was successful),
    # lets supply it directly as we know it using the "-o" option
        peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{"Args":["matrixMultiplication","5"]}' substitute_tls>&log.txt
        res=$?
        cat log.txt
        verifyResult $res "Example chaincode invoke execution on PEER$p.org$1 failed "
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Example chaincode invoke transaction on PEER$p.org$1 on channel '$CHANNEL_NAME' is successful ===================== "
        echo
        sleep 2
    done
}

## Create channel
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Creating channel..."
createChannel

## Join all the peers to the channel
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Having all peers join the channel..."
joinChannel 1
joinChannel 2

## Set the anchor peers for each org in the channel
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Updating anchor peers for org1..."
updateAnchorPeers 0 1
updateAnchorPeers 0 2

## Install chaincode on Peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Installing chaincode on peers..."
installExampleChaincode 1
installExampleChaincode 2
installBenchcontractChaincode 1
installBenchcontractChaincode 2

##Instantiate example and benchcontract chaincode on peer 0
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Instantiating example and benchcontract chaincode on peers..."
instantiateExampleChaincode 1
instantiateBenchcontractChaincode 1

##Query example and benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Querying example and benchcontract chaincode on all peers"
exampleChaincodeQuery 1
exampleChaincodeQuery 2
benchcontractChaincodeQuery 1
benchcontractChaincodeQuery 2

##Invoke example and benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Invoking example and benchcontract chaincode on all peers"
exampleChaincodeInvoke 1
exampleChaincodeInvoke 2
benchcontractChaincodeInvoke 1
benchcontractChaincodeInvoke 2

##Query example and benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')Querying example and benchcontract chaincode on all peers"
exampleChaincodeQuery 1
exampleChaincodeQuery 2
benchcontractChaincodeQuery 1
benchcontractChaincodeQuery 2

echo
echo

echo ""
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