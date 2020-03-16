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

const config = require("/.config.json")

const client = "~/tezos/tezos-client --addr " + config.ip + " --port 18730"

function execShellCommand(cmd) {
   const exec = require('child_process').exec;
   return new Promise((resolve, reject) => {
       exec(cmd, (error, stdout, stderr) => {
           if (error) {
               console.warn(error);
           }
           resolve(stdout? stdout : stderr);
       });
   });
}


class tezos {

  async init() {
    return Promise.resolve(1);
  }

  async writeData(value, from, to) {

      let result = await execShellCommand(client + " transfer " + value + " from " + from + " to " + to).catch(err => {
          console.log("An error occurred");
          return Promise.reject("Error");
      });
      console.log("Sent transaction with response " + result);
      return Promise.resolve();
  }

  async readData(account) {

    let value = await execShellCommand(client + " get balance for " + account).catch(err => {
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

module.exports = tezos;
