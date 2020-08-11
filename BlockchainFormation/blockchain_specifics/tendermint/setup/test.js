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

const Tendermint_Caller = require('./tendermint.js');
const tendermint_caller = new Tendermint_Caller();

async function test() {

    console.log("");
    console.log("===Starting the test===");
    console.log("");

    //initializing the contracts
    await tendermint_caller.init().catch(err => {
        console.log(err);
    })

    //writing a key value pair
    let start = Date.now();
    await tendermint_caller.writeData("Hallo", "Du").catch(err => {
        console.log(err);
    })
    console.log("Wrote data with key <Hallo> and value <Du>");
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    await tendermint_caller.close().catch(err => {
        console.log(err);
    })
}

test()
