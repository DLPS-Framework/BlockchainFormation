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

const level = require('level');
const db = level('my-db');
// 1) Create our database, supply location and options.
//    This will create or open the underlying store.

class levelDB {

  async init() {
    return Promise.resolve(1);
  }

  async writeData(key, value) {

    await db.put(key, value).catch(err => {
      console.log("An error occurred");
      return Promise.reject("Error");
    });
    console.log("Wrote key " + key);
    return Promise.resolve();
  }

  async readData(key) {

    let value = await db.get(key).catch(err => {
      console.log("An error occurred");
      return Promise.reject("Error");
    });
    console.log("Read value " + value);
    return Promise.resolve(value);
  }

  async matrixMultiplication(n) {
        // console.log(n)
    async function multiplyMatrices(m1, m2) {
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
        //console.log(i);
        m1[i] = [];
        for (var j = 0; j < n; j++) {
            m1[i][j] = f;
            f++;
        }
    }

    var m2 = m1;

    var result = await multiplyMatrices(m1, m2).catch(err => console.log(err()));

    var matrixSum = 0;

    for (var i = 0; i < result.length; ++i) {
        for (var j = 0; j < result[i].length; ++j) {
            matrixSum += result[i][j];
        }
    }
    return Promise.resolve(matrixSum.toString());
  }


  async close() {
    return Promise.resolve(1);
  }
}

module.exports = levelDB;
