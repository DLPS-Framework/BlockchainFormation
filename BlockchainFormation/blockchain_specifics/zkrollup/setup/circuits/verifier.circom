include "./circuits/mimc.circom";
include "./circuits/mimcsponge.circom"
include "./circuits/eddsamimcsponge.circom"

template HashLeftRight() {
  signal input left;
  signal input right;

  signal output hash;

  component hasher = MiMCSponge(2, 220, 1);
  left ==> hasher.ins[0];
  right ==> hasher.ins[1];
  hasher.k <== 0;

  hash <== hasher.outs[0];
}

template Selector() {
  signal input input_elem;
  signal input path_elem;
  signal input path_index;

  signal output left;
  signal output right;

  signal left_selector_1;
  signal left_selector_2;
  signal right_selector_1;
  signal right_selector_2;

  path_index * (1-path_index) === 0

  left_selector_1 <== (1 - path_index)*input_elem;
  left_selector_2 <== (path_index)*path_elem;
  right_selector_1 <== (path_index)*input_elem;
  right_selector_2 <== (1 - path_index)*path_elem;

  left <== left_selector_1 + left_selector_2;
  right <== right_selector_1 + right_selector_2;
}

template GetMerkleRoot(levels) {

    signal input leaf;
    signal input path_index[levels];
    signal input path_elements[levels];

    signal output out;

    component selectors[levels];
    component hashers[levels];

    for (var i = 0; i < levels; i++) {
      selectors[i] = Selector();
      hashers[i] = HashLeftRight();

      path_index[i] ==> selectors[i].path_index;
      path_elements[i] ==> selectors[i].path_elem;

      selectors[i].left ==> hashers[i].left;
      selectors[i].right ==> hashers[i].right;
    }

    leaf ==> selectors[0].input_elem;

    for (var i = 1; i < levels; i++) {
      hashers[i-1].hash ==> selectors[i].input_elem;
    }

    out <== hashers[levels - 1].hash;
}


template HashedLeaf() {

    signal input pubkey[2];
    signal input balance;
    signal output out;

    component txLeaf = MiMCSponge(3, 220, 1);
    txLeaf.ins[0] <== pubkey[0];
    txLeaf.ins[1] <== pubkey[1];
    txLeaf.ins[2] <== balance;
    txLeaf.k <== 0;

    out <== txLeaf.outs[0];
}

template MessageHash(n) {
    signal input ins[n];
    signal output out;

    component msg_hasher = MiMCSponge(n, 220, 1);
    for (var i=0; i<n; i++) {
        msg_hasher.ins[i] <== ins[i];
    }
    msg_hasher.k <== 0;

    out <== msg_hasher.outs[0];
}

template verifier(levels) {

    //the root of the balance tree
    signal input root;

    // the account information
    signal input account_balance;
    signal input account_pubkey[2];

    signal private input account_path_element[levels];
    signal private input account_path_ids[levels];


    //__1. verify sender account existence
    component accountLeaf = HashedLeaf();
    accountLeaf.pubkey[0] <== account_pubkey[0];
    accountLeaf.pubkey[1] <== account_pubkey[1];
    accountLeaf.balance <== account_balance;

    component accountExistence = GetMerkleRoot(levels);
    accountExistence.leaf <== accountLeaf.out;
    for (var i=0; i<levels; i++) {
        accountExistence.path_index[i] <== account_path_ids[i];
        accountExistence.path_elements[i] <== account_path_element[i];
    }

    accountExistence.out === root;

}

component main = verifier(4);
