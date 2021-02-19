

createChannel() {

    setGlobals 0 1
    peer channel create -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/$CHANNEL_NAME.tx substitute_tls>&log.txt
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
    peer channel update -o orderer1.example.com:7050 -c $CHANNEL_NAME -f ./channel-artifacts/${CORE_PEER_LOCALMSPID}anchors${CHANNEL_NAME}.tx substitute_tls>&log.txt
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

echo
echo
echo "========= All GOOD, script completed =========== "

exit 0