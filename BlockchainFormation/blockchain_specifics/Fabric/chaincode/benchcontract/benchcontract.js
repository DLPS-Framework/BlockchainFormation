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

'use strict';

// Fabric smart contract classes
const { Contract, Context } = require('fabric-contract-api');



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
        super('org.bench.benchcontract');
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
    async instantiate(ctx) {
        // No implementation required with this example
        // It could be where data migration is performed, if necessary
        console.log('Instantiate the contract')
    }

    /** Standard seters and geters
     * @param {String} key  Primary key
     * @param {String|Object} data value to store
     */

    async writeData(ctx, _key, _value) {
        await ctx.stub.putState(_key.toString(), Buffer.from(_value))
        return Buffer.from('1')
    }

    async readData(ctx, _key) {
        var tmp = await ctx.stub.getState(_key.toString())
        return Buffer.from(tmp.toString())
    }

    async writeMuchData(ctx, len, start, delta) {
        for (var i = start; i < start+len; i++) {
            await ctx.stub.putState(i.toString(), (delta + i).toString())
        }
        return Buffer.from('1')
    }

    async readMuchData(ctx, _start, _end) {
        var sum = 0
        for (var i = _start; i < _end; i++) {
            var tmp = await ctx.stub.getState(i.toString())
            console.log(sum)
            sum += Number(tmp)
        }
        return Buffer.from(sum.toString())
    }


    /** For overhead testing
    */
    async doNothing(ctx) {
        return Buffer.from('1')
    }

    /** Function for matrix multiplication
     * @param {Number} n number of rows/ columns
     */
    async matrixMultiplication(ctx, n) {
        console.log(n)
        function multiplyMatrices(m1, m2) {
            var result = []
            for (var i = 0; i < m1.length; i++) {
                result[i] = []
                for (var j = 0; j < m2[0].length; j++) {
                    var sum = 0
                    for (var k = 0; k < m1[0].length; k++) {
                        sum += m1[i][k] * m2[k][j]
                    }
                    result[i][j] = sum
                }
            }
            return result
        }

        var f = 1
        var m1 = [];
        for (var i = 0; i < n; i++) {
            console.log(i)
            m1[i] = [];
            for (var j = 0; j < n; j++) {
                m1[i][j] = f
                f++
            }
        }

        var m2 = m1

        var result = multiplyMatrices(m1, m2)

        var matrixSum = 0

        for (var i = 0; i < result.length; ++i) {
            for (var j = 0; j < result[i].length; ++j) {
                matrixSum += result[i][j];
            }
        }
        return Buffer.from(matrixSum.toString())
    }

    async setMatrixMultiplication(ctx, n) {
        var res = await this.matrixMultiplication(ctx, n)
        await ctx.stub.putState("tmp", res.toString())
        return Buffer.from(res.toString())
    }

}

module.exports = BenchContract;
