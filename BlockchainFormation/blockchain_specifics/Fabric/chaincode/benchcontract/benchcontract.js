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

/*
SPDX-License-Identifier: Apache-2.0
*/

"use strict";

// Fabric smart contract classes
const { Contract, Context } = require("fabric-contract-api");

/**
 * Custom context
 */
class BenchContext extends Context {
    constructor() {
        super();
    }
}

/**
 * Define smart contract by extending Fabric Contract class
 *
 */
class BenchContract extends Contract {
    constructor() {
        // Unique namespace when multiple contracts per chaincode file
        super("org.bench.benchcontract");
    }

    /**
     * Define a custom context
     */
    createContext() {
        return new BenchContext();
    }

    /**
     * Instantiate to perform any setup of the ledger that might be required.
     * @param {Context} ctx the transaction context
     */
    async instantiate(ctx, len) {
        // No implementation required with this example
        // It could be where data migration is performed, if necessary
        console.log("Instantiate the contract");
        console.log(len);
        var promiseArray = [];
        for (var i = parseInt(0, 10); i < parseInt(len, 10); i++) {
            promiseArray.push(ctx.stub.putState("key_" + i.toString(), Buffer.from(JSON.stringify({ value: i }))));
        }
        await Promise.all(promiseArray);
        return Buffer.from("1");
    }

    /** Standard setters and getters
     * @param {Context} ctx the transaction context
     * @param {String} key  Primary key
     * @param {String|Object} value: value to store
     */

    async writeData(ctx, key, value) {
        await ctx.stub.putState("key_" + key, Buffer.from("value_" + value));
        return Buffer.from("1");
    }

    async writeDataPrivate(ctx, name, key, value) {
        await ctx.stub.putPrivateData(name, "key_" + key, Buffer.from("value_" + value));
        return Buffer.from("2");
    }

    async writeDataPublicBufferPeer(ctx, key, bufferSize) {
        const buffer = new Buffer(Number(bufferSize));
        await ctx.stub.putState("key_" + key, Buffer.from("value_" + buffer.toString()));
        return Buffer.from("1");
    }

    async writeDataPrivateBufferPeer(ctx, name, key, bufferSize) {
        const buffer = new Buffer(Number(bufferSize));
        await ctx.stub.putPrivateData(name, "key_" + key, Buffer.from("value_" + buffer.toString()));
        return Buffer.from("2");
    }

    async writeDataPrivateImplicit(ctx, name, key, value) {
        var collectionArray = name.split(",");
        var promiseArray = [];
        collectionArray.forEach(element => {
            promiseArray.push(ctx.stub.putPrivateData(element, key.toString(), Buffer.from(value)));
        });
        await Promise.all(collectionArray);
        return Buffer.from("2");
    }

    /** Standard setters and getters
     * @param {Context} ctx the transaction context
     * @param {String} key  Primary key
     */

    async readData(ctx, key) {
        var tmp = await ctx.stub.getState("key_" + key);
        console.log(tmp);
        return Buffer.from(tmp.toString());
    }

    async readDataPrivate(ctx, name, key) {
        var tmp = await ctx.stub.getPrivateData(name, "key_" + key);
        return Buffer.from(tmp.toString());
    }

    /** Standard setters and getters
     * @param {Context} ctx the transaction context
     * @param {String} len The number of writes
     * @param {String} start The index of the first write
     * @param {String} delta The offset of key and value
     */

    async writeMuchData(ctx, len, start, delta) {
        var promiseArray = [];
        for (var i = parseInt(start, 10); i < parseInt(start, 10) + parseInt(len, 10); i++) {
            promiseArray.push(ctx.stub.putState("key_" + i.toString(), Buffer.from((parseInt(delta, 10) + i).toString())));
        }
        await Promise.all(promiseArray);
        return Buffer.from("1");
    }

    async writeMuchDataPrivate(ctx, name, len, start, delta) {
        var promiseArray = [];
        for (var i = parseInt(start, 10); i < parseInt(start, 10) + parseInt(len, 10); i++) {
            promiseArray.push(ctx.stub.putPrivateData(name, "key_" + i.toString(), Buffer.from((parseInt(delta, 10) + i).toString())));
        }
        await Promise.all(promiseArray);
        return Buffer.from("2");
    }

    async writeMuchData2(ctx, len, start, delta) {
        var aggregate_key = {};
        for (var i = 0; i < parseInt(len, 10); i++) {
            aggregate_key["key_" + i.toString()] = (i + delta).toString();
        }
        console.log(JSON.stringify(aggregate_key));
        await ctx.stub.putState("key_" + start.toString(), Buffer.from(JSON.stringify(aggregate_key)));
        return Buffer.from("1");
    }

    /** Standard setters and getters
     * @param {Context} ctx the transaction context
     * @param {String} len The number of writes
     * @param {String} start The index of the first write
     */
    async readMuchData(ctx, len, start) {
        var promiseArray = [];
        var sum = 0;
        for (var i = parseInt(start, 10); i < parseInt(start, 10) + parseInt(len, 10); i++) {
            promiseArray.push(
                ctx.stub.getState("key_" + i.toString()).then(res => {
                    sum += res;
                })
            );
        }
        await Promise.all(promiseArray);
        return Buffer.from(sum.toString());
    }

    async readMuchDataPrivate(ctx, name, len, start) {
        var promiseArray = [];
        var sum = 0;
        for (var i = parseInt(start, 10); i < parseInt(start, 10) + parseInt(len, 10); i++) {
            promiseArray.push(
                ctx.stub.getPrivateData(name, "key_" + i.toString()).then(res => {
                    sum += res;
                })
            );
        }
        await Promise.all(promiseArray);
        return Buffer.from(sum.toString());
    }

    async readMuchData2(ctx, len, start) {
        var sum = 0;
        try {
            var tmp = await ctx.stub.getState("key_" + start.toString());
            console.log(tmp);
            var tmp2 = JSON.parse(tmp);
            console.log(tmp2);
        } catch (err) {
            console.log(err);
        }
        try {
            console.log(JSON.stringify(tmp2));
            for (var i = 0; i < parseInt(len, 10); i++) {
                sum += Number(tmp2["key_" + i.toString()]);
            }
        } catch (err) {
            console.log(err);
        }
        return Buffer.from(sum.toString());
    }

    /** For overhead testing
     * @param {Context} ctx the transaction context
     */
    async doNothing(ctx) {
        return Buffer.from("1");
    }

    /** Function for matrix multiplication
     * @param {Number} n number of rows/ columns
     */
    async matrixMultiplication(ctx, n) {
        // console.log(n)
        function multiplyMatrices(m1, m2) {
            var result = [];
            for (var i = 0; i < m1.length; i++) {
                result[i] = [];
                for (var j = 0; j < m2[0].length; j++) {
                    var sum = 0;
                    for (var k = 0; k < m1[0].length; k++) {
                        sum += m1[i][k] * m2[k][j];
                    }
                    result[i][j] = sum;
                }
            }
            return result;
        }

        var f = 1;
        var m1 = [];
        for (var i = 0; i < n; i++) {
            console.log(i);
            m1[i] = [];
            for (var j = 0; j < n; j++) {
                m1[i][j] = f;
                f++;
            }
        }

        var m2 = m1;

        var result = multiplyMatrices(m1, m2);

        var matrixSum = 0;

        for (var i = 0; i < result.length; ++i) {
            for (var j = 0; j < result[i].length; ++j) {
                matrixSum += result[i][j];
            }
        }
        return Buffer.from(matrixSum.toString());
    }

    async setMatrixMultiplication(ctx, n) {
        var res = await this.matrixMultiplication(ctx, n);
        await ctx.stub.putState("tmp", res.toString());
        return Buffer.from(res.toString());
    }

    async complexQuery(ctx, value) {
        const allResults = [];
        var query = {
            selector: {
                value: {
                    $eq: Number(value)
                }
            }
        };
        var iterator = await ctx.stub.getQueryResult(JSON.stringify(query));
        while (true) {
            const res = await iterator.next();
            if (res.value) {
                // if not a getHistoryForKey iterator then key is contained in res.value.key
                allResults.push(res.value.value.toString("utf8"));
            }

            // check to see if we have reached then end
            if (res.done) {
                // explicitly close the iterator
                await iterator.close();
                return Buffer.from(allResults.toString());
            }
        }
    }

    async complexQueryPrivate(ctx, name, value) {
        const allResults = [];
        var query = {
            selector: {
                value: {
                    $eq: Number(value)
                }
            }
        };
        var iterator = await ctx.stub.getPrivateDataQueryResult(name, JSON.stringify(query));
        while (true) {
            const res = await iterator.next();
            if (res.value) {
                // if not a getHistoryForKey iterator then key is contained in res.value.key
                allResults.push(res.value.value.toString("utf8"));
            }

            // check to see if we have reached then end
            if (res.done) {
                // explicitly close the iterator
                await iterator.close();
                return Buffer.from(allResults.toString());
            }
        }
    }

    async ccQuery(ctx, from, to) {
        const startKey = from;
        const endKey = to;
        const allResults = [];
        for await (const {key, value} of ctx.stub.getStateByRange(startKey, endKey)) {
            const strValue = Buffer.from(value).toString('utf8');
            let record;
            try {
                record = JSON.parse(strValue);
            } catch (err) {
                console.log(err);
                record = strValue;
            }
            allResults.push({ Key: key, Record: record });
        }
        console.info(allResults);
        return Buffer.from(allResults.length.toString());
    }
}

module.exports = BenchContract;
