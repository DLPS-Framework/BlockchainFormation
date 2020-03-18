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

const levelDB = require("./leveldb.js")
const leveldb = new levelDB();

async function test() {

    console.log("");
    console.log("===Starting the test===");
    console.log("");

    //initializing the contracts
    await leveldb.init().catch(err => {
        console.log(err);
    })

    //writing a key value pair
    start = Date.now();
    await leveldb.writeData("Hallo", "Du").catch(err => {
        console.log(err);
    })
    console.log("Wrote data with key <Hallo> and value <Du>");
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    start = Date.now()
    result = await leveldb.readData("Hallo").catch(err => {
        console.log(err);
    });
    console.log("Result from readData on key <Hallo>: " + result);
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    start = Date.now()
    result = await leveldb.readData("Test").catch(err => {
        console.log("Key <Test> does not exist");
    });
    console.log("Result from readData on key <Test>: " + result);
    console.log("elapsed time: " + (Date.now() - start));
    console.log("");
    console.log("=======================");
    console.log("");

    await leveldb.close().catch(err => {
        console.log(err);
    })
}

test()
