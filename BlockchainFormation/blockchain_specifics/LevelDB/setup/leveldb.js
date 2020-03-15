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

  async close() {
    return Promise.resolve(1);
  }
}

module.exports = levelDB;
