/*
 * Copyright 2019  ChainLab
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

const tezos = require("./tezos.js")
const tezos_client = new tezos();

async function test() {

    console.log("");
    console.log("===Starting the test===");
    console.log("");

    //initializing the contracts
    await tezos_client.init().catch(err => {
        console.log(err);
    })

    //getting the balance
    start = Date.now()
    result = await tezos_client.readData("tz1SyK4X7xaarzjXoQmzjh9toWGMn9NRBv8t").catch(err => {
        console.log(err);
    });
    console.log("Balance of tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx: " + result);
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    //Sending a transaction
    start = Date.now();
    await tezos_client.writeData("100", "tz1SyK4X7xaarzjXoQmzjh9toWGMn9NRBv8t", "tz1WFYojFoYHjEnMJMN3inPdcqmdacbkDm93").catch(err => {
        console.log(err);
    })
    console.log("Sent 100 from tz1 to tz2");
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    //getting the new balance
    start = Date.now()
    result = await tezos_client.readData("tz1SyK4X7xaarzjXoQmzjh9toWGMn9NRBv8t").catch(err => {
        console.log(err);
    });
    console.log("Balance of tz1KqTpEZ7Yob7QbPE4Hy4Wo8fHG8LhKxZSx: " + result);
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    await tezos_client.close().catch(err => {
        console.log(err);
    })
}

test()
