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

// 1) Create our database, supply location and options.
//    This will create or open the underlying store.

const fetch = require("node-fetch")


class tendermint_caller {

  async init() {
    return Promise.resolve(1);
  }

  async writeData(key, value) {

      let url = 'http://127.0.0.1:26657/broadcast_tx_commit?tx="' + key + '"'

	  let response = await fetch(url, {
	      method: "GET",
	      headers: {"Content-Type": "application/octet-stream"}
	  }).catch(err => {return Promise.reject(err)})

	  let json = await response.json().catch(err => {return Promise.reject(err)});
          if (json.hasOwnProperty('result')) {
              console.log("Success")
              // console.log(json.result)
              console.log(json.result.hash)
	      return Promise.resolve(json.result.hash)
          } else if (json.hasOwnProperty('error')) {
              console.log("Error")
              if (json.error.hasOwnProperty('data')) {
                  //console.log(json.error.data)
                  return Promise.reject(json.error.data)
              } else {
                 return Promise.reject(json)
              }
          } else {
              console.log("Other error")
              console.log(json)
              //console.log(json.message)
              return Promise.reject(json.message)
          }
  };

  async readData(key) {
      let url = 'http://127.0.0.1:26657/abci_query?data="' + key + '"'

	  let response = await fetch(url, {
	      method: "GET",
	      headers: {"Content-Type": "application/octet-stream"}
	  }).catch(err => {return Promise.reject(err)})

	  let json = await response.json().catch(err => {return Promise.reject(err)});
          if (json.hasOwnProperty('result')) {
              try {
                  console.log(json.result.response.log)
                  let log = json.result.response.log
                  if (log == "exists") {
                      console.log("SUCCESS")
                      return Promise.resolve("exists")
                  } else if (log == "does not exist") {
                      console.log("SUCCESS")
                      return Promise.resolve("does not exist")
                  } else {
                      console.log("ERROR")
                      console.log(json)
                      return Promise.reject(json)
                  }

              } catch (err) {
                  console.log("ERROR")
                  console.log(err)
                  return Promise.reject(err)
              }
          } else {
              console.log("Other error")
              console.log(json)
              //console.log(json.message)
              return Promise.reject(json.message)
          }
  };

  async close() {
    return Promise.resolve(1);
  }
}

module.exports = tendermint_caller;
