const fs = require("fs")

const snarkjs = require("snarkjs");
const eddsa = require("circomlib/src/eddsa.js");
const mimcsponge = require("circomlib/src/mimcsponge.js")
const {stringifyBigInts} = require('snarkjs/src/stringifybigint.js');

const seedIssuer = "0001020304050607080900010203040506070809000102030405060708090001";
const seedHolder = "00010203040506070809000102030405060708090001020304050607080900AA";
const bigInt = snarkjs.bigInt;

var crypto = require('crypto')

const attributes = ["name: Johannes", "Job: Student", "", ""]
const hashes = []
for (let i=0; i < attributes.length; i++) {
    let shasum = crypto.createHash('sha1')
    shasum.update(attributes[i])
    hashes.push(shasum.digest('hex'))
}

const bigInts = []
for (let i=0; i< hashes.length; i++) {
    bigInts.push(hex2int(hashes[i]))
}

console.log("Attributes: ")
console.log(attributes)

console.log("Hashes: ")
console.log(hashes)

console.log("BigInts: ")
console.log(bigInts)

const level = 2


function hex2int(hexstring) {
    var result = "";
    for (let i=0; i<hexstring.length; i++) {
        if (parseInt(hexstring[i])< 10) {
            result += "0"
        }
        result += parseInt(hexstring[i], 16);
    }
    //console.log(result);
    return BigInt(result);
}

function int2hex(decstring) {
    var result = ""
    if (decstring.length % 2 != 0) {
        console.log(decstring);
        throw("Not a valid decstring: Odd number of chars");
    }
    for (let i=0; i<decstring.length/2; i++) {
        var sym = parseInt(decstring.substring(2*i, 2*(i+1)));
        if (sym<16) {
            result += sym.toString(16);
        } else {
            console.log(decstring);
            console.log(i);
            console.log(sym);
            throw("Not a valid decstring");
        }
    }
    //console.log(result);
}



function createKeypair(seed) {

    const prvKey = Buffer.from(seed, "hex");
    const pubKey = eddsa.prv2pub(prvKey);

    //console.log("Private Key: " + prvKey)
    //console.log("Public Key: " + pubKey)

    return {
        "prvkey": prvKey,
        "pubkey": pubKey
    }

}

function credential_sample()
{
    //
    // init merkle tree
    //
    var tree = init_merkle_tree(level)

    console.log("Initial tree:")
    console.log(tree)
    fs.writeFileSync('tree.json', JSON.stringify(stringifyBigInts(tree), null, 4));

    const accIssuer = createKeypair(seedIssuer)
    const accHolder = createKeypair(seedHolder)
    for (let index=0; index<2**level; index++) {
        tree = insert_merkle_tree(level, tree, index, bigInts[index])
    }
    console.log("Credential tree:")
    console.log(tree)

    //
    // sign root
    //
    const signature = eddsa.signMiMCSponge(accIssuer.prvkey, tree.root);
    console.log("Signature: ");
    console.log(signature);
    if(!eddsa.verifyMiMCSponge(tree.root, signature, accIssuer.pubkey)){
        console.log("\nsignature not matched\n");
    }

    //
    // calculate final root
    //
    console.log("root: ", tree.root)
    fs.writeFileSync('tree1.json', JSON.stringify(stringifyBigInts(tree), null, 4));

    const inputs2 = {
        "root": tree.root,
        "signature": signature["S"],
        "issuer_signature_r": signature["R8"],
        "issuer_pubkey": accIssuer.pubkey,
        "bigNumber": bigInts[3],
        "path_idx": tree.path_index,
        "path_element": tree.path_elements

    }

    console.log("Writing input2 to input2.json")
    fs.writeFileSync('input2.json', JSON.stringify(stringifyBigInts(inputs2), null, 4));

    return {
        "root": tree.root,
        "signature": signature,
        "issuer_pubkey": accIssuer.pubkey
    }
}

const inputs = credential_sample()
console.log(JSON.parse(JSON.stringify(stringifyBigInts(inputs))))

console.log("Writing input to input.json")
fs.writeFileSync('input.json', JSON.stringify(stringifyBigInts(inputs), null, 4));


///
/// merkle tree
///
function init_merkle_tree(n_levels) {
    let tree = [];
    for (let i = 0; i < n_levels; i++) {
      let tree_level = [];
      for (let j = 0; j < Math.pow(2, n_levels - i); j++) {
        if (i == 0) {
                tree_level.push(mimcsponge.multiHash([BigInt(0)]));
        } else {
            tree_level.push(mimcsponge.multiHash([tree[i-1][2*j], tree[i-1][2*j+1]]));
        }
      }
      tree.push(tree_level);
    }
    const root = mimcsponge.multiHash([ tree[n_levels - 1][0], tree[n_levels - 1][1] ]);

    return {"tree": tree, "root":root}
}

function get_inter_elements(n_levels, tree, index) {
    let current_index = index;
    let path_index = [];
    let path_elements = [];

    for (let i = 0; i < n_levels; i++) {
      if (current_index % 2 == 0) {
        path_elements.push(tree[i][current_index + 1])
      } else {
        path_elements.push(tree[i][current_index - 1])
      }

      path_index.push(current_index % 2);
      current_index = Math.floor(current_index / 2);
    }
    const root = mimcsponge.multiHash([ tree[n_levels - 1][0], tree[n_levels - 1][1] ]);

    return {
        "root":root,  
        "path_elements": path_elements,
        "path_index": path_index
    };
}

function insert_merkle_tree(n_levels, complete_tree, index, leaf) {
    let current_index = index;
    let path_index = [];
    let path_elements = [];
    let localTree = [];
    let tree = complete_tree.tree;

    for (let i = 0; i < n_levels; i++) {
      let tree_level = [];
      path_index.push(current_index % 2);
      for (let j = 0; j < Math.pow(2, n_levels - i); j++) {
        if (i == 0) {
          if (j == index) {
            tree_level.push(bigInt(leaf));
          } else {
            tree_level.push(tree[0][j])
          }
        } else {
            tree_level.push(mimcsponge.multiHash([ localTree[i-1][2*j], localTree[i-1][2*j+1] ]));
        }
      }

      if (current_index % 2 == 0) {
        path_elements.push(tree_level[current_index + 1]);
      } else {
        path_elements.push(tree_level[current_index - 1]);
      }

      localTree.push(tree_level)
      current_index = Math.floor(current_index / 2);
    }

    const root = mimcsponge.multiHash([ localTree[n_levels - 1][0], localTree[n_levels - 1][1] ]);

    return {
        "root":root,
        "tree" :localTree,
        "path_index": path_index,
        "path_elements": path_elements
    };
};


