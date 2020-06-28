const zkSnark = require("snarkjs");
const fs = require("fs");
const {stringifyBigInts, unstringifyBigInts} = require("./node_modules/snarkjs/src/stringifybigint.js");

const circuitDef = JSON.parse(fs.readFileSync("circuit.json", "utf8"));
const circuit = new zkSnark.Circuit(circuitDef);

console.log("Number of constraints: " + circuit.nConstraints);

console.log("===========");
console.log("Verifying proof");


const vk_verifier = JSON.parse(fs.readFileSync("verification_key.json", "utf8"));
const proof = JSON.parse(fs.readFileSync("proof.json", "utf8"));
const publicSignals = JSON.parse(fs.readFileSync("public.json", "utf8"));

const start = Date.now()


if (zkSnark.original.isValid(unstringifyBigInts(vk_verifier), unstringifyBigInts(proof), unstringifyBigInts(publicSignals))) {
    console.log("The proof is valid");
} else {
    console.log("The proof is not valid");
}

const end = Date.now()

console.log("Time for verification: " + (end - start) + "ms");