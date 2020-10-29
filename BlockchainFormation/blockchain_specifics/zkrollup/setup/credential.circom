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

template credential(levels) {

    signal private input root;
    signal private input issuer_signature_r[2];
    signal private input signature

    // the attribute; in form sha1sum | hex2dec | bigNumber
    signal private input bigNumber;

    signal private input path_idx[levels];
    signal private input path_element[levels];

    signal input issuer_pubkey[2];


    //__1. verify attribute existence;
    component attributeExistence = GetMerkleRoot(levels);
    attributeExistence.leaf <== bigNumber;
    for (var i=0; i<levels; i++) {
        attributeExistence.path_index[i] <== path_idx[i];
        attributeExistence.path_elements[i] <== path_element[i];
    }
    attributeExistence.out === root;

    //__2. verify signature
    component sigVerifier = EdDSAMiMCSpongeVerifier();
    sigVerifier.enabled <== 1;
    sigVerifier.Ax <== issuer_pubkey[0]
    sigVerifier.Ay <== issuer_pubkey[1];
    sigVerifier.R8x <== issuer_signature_r[0];
    sigVerifier.R8y <== issuer_signature_r[1];
    sigVerifier.S <== signature
    sigVerifier.M <== root

}

component main = credential(2);
