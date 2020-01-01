

createChannel() {

    setGlobals 0 1
    peer channel create -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/channel.tx substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Channel creation failed"
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Channel \"$CHANNEL_NAME\" is created successfully ===================== "
    echo
}

updateAnchorPeers() {
    PEER=$1
    ORG=$2
    setGlobals $PEER $ORG
    peer channel update -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/${CORE_PEER_LOCALMSPID}anchors.tx substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Anchor peer update failed"
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Anchor peers for org \"$CORE_PEER_LOCALMSPID\" on \"$CHANNEL_NAME\" is updated successfully ===================== "
    echo
}

## Sometimes Join takes time hence RETRY atleast for 5 times
joinWithRetry () {
    PEER=$1
    peer channel join -b $CHANNEL_NAME.block substitute_tls>&log.txt
    res=$?
    cat log.txt
    if [ $res -ne 0 -a $COUNTER -lt $MAX_RETRY ]; then
        COUNTER=` expr $COUNTER + 1`
        echo "PEER$PEER failed to join the channel, Retry after 5 seconds"
        sleep 5
        joinWithRetry $PEER
    else
        COUNTER=1
    fi
    verifyResult $res "After $MAX_RETRY attempts, PEER$PEER has failed to Join the Channel"
}

joinChannel () {
    PEER=$1
    ORG=$2
    setGlobals $PEER $ORG
    joinWithRetry $PEER
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== PEER$PEER.ORG$ORG joined on the channel \"$CHANNEL_NAME\" ===================== "
    echo
}

installBenchcontractChaincode () {
    PEER=$1
    ORG=$2
    setGlobals $PEER $ORG
    peer chaincode install -l node -n benchcontract -v 1.0 -p /opt/gopath/src/github.com/hyperledger/fabric/examples/chaincode/benchcontract substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Benchcontract chaincode installation on remote peer PEER$PEER.ORG$ORG has Failed"
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode successfully installed on remote peer PEER$PEER.ORG$ORG ===================== "
    echo
}

instantiateBenchcontractChaincode () {
    PEER=$1
    ORG=$2
    setGlobals $PEER $ORG
    peer chaincode instantiate -o orderer1.example.com:7050 -C $CHANNEL_NAME -l node -n benchcontract -v 1.0 -c '{"Args":["org.bench.benchcontract:instantiate"]}' -P 'substitute_endorsement' substitute_tls>&log.txt
    res=$?
    cat log.txt
    verifyResult $res "Benchcontract chaincode instantiation on PEER$PEER.orgORG1 on channel '$CHANNEL_NAME' failed"
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode instantiation on PEER$PEER.ORG$ORG on channel '$CHANNEL_NAME' was successful ===================== "
    echo
}

benchcontractChaincodeQuery () {
    PEER=$1
    ORG=$2
    setGlobals $PEER $ORG
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Querying benchcontract chaincode on PEER$PEER.ORG$ORG on channel '$CHANNEL_NAME'... ===================== "
    local rc=1
    local starttime=$(date +%s)

    # continue to poll
    # we either get a successful response, or reach TIMEOUT
    while test "$(($(date +%s)-starttime))" -lt "$TIMEOUT" -a $rc -ne 0
    do
        sleep 10
        echo "Attempting to query benchcontract chaincode on PEER$PEER.ORG$ORG ...$(($(date +%s)-starttime)) secs"
        # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args":["doNothing"]}' >& log.txt \
        # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args:["writeData", "testkey", "testvalue"]}' substitute_tls >& log.txt \
        peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{"Args":["matrixMultiplication","3"]}' substitute_tls >& log.txt \
        # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args:["readData", "testkey"]}' substitute_tls >& log.txt \
        # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args:["writeMuchData", "100", "10", "90"]}' substitute_tls >& log.txt \
        # peer chaincode query -C $CHANNEL_NAME -n benchcontract -c '{Args:["readMuchData", "20", "30"]}' substitute_tls >& log.txt
        # res=$?
        # cat log.txt
        # verifyResult $res "Benchcontract chaincode instantiation on PEER$PEER.orgORG1 on channel '$CHANNEL_NAME' failed"
        # test $? -eq 0 && VALUE=$(cat log.txt | awk "/Query Result/ {print $NF}")
        # test "$VALUE" = "$2" && let rc=0
        test $? -eq 0 && let rc=0

    done
    echo
    cat log.txt
    if test $rc -eq 0 ; then
       echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode query on PEER$PEER.ORG$ORG on channel '$CHANNEL_NAME' was successful ===================== "
       echo
    else
        echo "!!!!!!!!!!!!!!! Benchcontract chaincode query result on PEER$PEER.ORG$ORG is INVALID !!!!!!!!!!!!!!!!"
        echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ================== ERROR !!! FAILED to execute End-2-End Scenario =================="
        echo
        exit 1
    echo
    echo
    echo
    fi
}

benchcontractChaincodeInvoke () {
    PEER=$1
    ORG=$2
    setGlobals $PEER $ORG
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Invoking benchcontract chaincode on PEER$PEER.ORG$ORG on channel '$CHANNEL_NAME'... ===================== "
    # while "peer chaincode" command can get the orderer endpoint from the peer (if join was successful),
    # lets supply it directly as we know it using the "-o" option
    # peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{Args":["doNothing"]}' >& log.txt && \
    # peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{Args:["writeData", "testkey", "testvalue"]}' substitute_tls >& log.txt && \
    peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{"Args":["matrixMultiplication","3"]}' substitute_tls >& log.txt \
    # peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{Args:["readData", "testkey"]}' substitute_tls >& log.txt && \
    # peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{Args:["writeMuchData", "100", "10", "90"]}' substitute_tls >& log.txt && \
    # peer chaincode invoke -o orderer1.example.com:7050 -C $CHANNEL_NAME -n benchcontract -c '{Args:["readMuchData", "20", "30"]}' substitute_tls >& log.txt
    res=$?
    cat log.txt
    verifyResult $res "Benchcontract chaincode invoke execution on PEER$PEER.ORG$ORG failed "
    echo "$(date +'%Y-%m-%d %H:%M:%S:%3N')   ===================== Benchcontract chaincode invoke transaction on PEER$PEER.ORG$ORG on channel '$CHANNEL_NAME' was successful ===================== "
    echo
    sleep 2
}

# Create the channel
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Creating channel..."
createChannel

# Join all the peers to the channel
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Having all peers join the channel..."
for PEER in substitute_enum_peers; do
    for ORG in substitute_enum_orgs; do
        joinChannel $PEER $ORG
    done
done

# Updating the anchor peers for each org in the channel
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Updating anchor peers for each org..."
for PEER in 0; do
    for ORG in substitute_enum_orgs; do
        updateAnchorPeers $PEER $ORG
    done
done

# Installing benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Installing chaincode on peers..."
for PEER in substitute_enum_peers; do
    for ORG in substitute_enum_orgs; do
        installBenchcontractChaincode $PEER $ORG
    done
done

#Instantiating benchcontract chaincode on peer0.org1
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Instantiating benchcontract chaincode on peer0.org1..."
for PEER in 0; do
    for ORG in 1; do
        instantiateBenchcontractChaincode $PEER $ORG
    done
done

#Querying example and benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Querying benchcontract chaincode on all peers"
for PEER in substitute_enum_peers; do
    for ORG in substitute_enum_orgs; do
        sleep 2
        benchcontractChaincodeQuery $PEER $ORG &
    done
done

wait

# Invoking benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Invoking benchcontract chaincode on all peers"
for PEER in substitute_enum_peers; do
    for ORG in substitute_enum_orgs; do
        benchcontractChaincodeInvoke $PEER $ORG &
    done
done

wait

# Querying benchcontract chaincode on all peers
echo "$(date +'%Y-%m-%d %H:%M:%S:%3N') Querying benchcontract chaincode on all peers"
for PEER in substitute_enum_peers; do
    for ORG in substitute_enum_orgs; do
        benchcontractChaincodeQuery $PEER $ORG &
    done
done

wait

echo
echo
echo "========= All GOOD, BMHN execution completed =========== "

exit 0