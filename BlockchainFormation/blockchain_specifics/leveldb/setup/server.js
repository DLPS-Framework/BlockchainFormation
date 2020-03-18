// Copyright 2020 ChainLab
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.


const http = require('http');
const leveldb = require('./leveldb.js');
const levelDB = new leveldb();

const config = require('./config.json');


async function writeData(key, value) {

    let result = await levelDB.writeData(key, value).catch(err => {
        console.log(err);
        throw("Error");
    });
    return result;
}

async function readData(key) {

    let response = await levelDB.readData(key).catch(err => {
        console.log(err);
        throw("Error");
    });
    console.log("Returning " + response);
    return response;
}


const server = http.createServer();

server.on("request", async (req, res) => {

    try {

        console.log("url: " + req.url);
        console.log("method: " + req.method);
        console.log("data: " + req.headers['content-type']);

        let data = [];

        req.on('data', chunk => {
            console.log(`Data chunk available: ${chunk}`);
            data.push(chunk);
        });

        req.on('end', async () => {

            try {
                console.log("Data: " + JSON.stringify(JSON.parse(data)));
                if (req.method == "POST") {

                    if (req.url == "/writeData") {

                        let dataJson = JSON.parse(data);
                        let key = dataJson['key'];
                        let value = dataJson['value'];
                        console.log("key: " + key);
                        console.log("value: " + value);

                        await writeData(key, value).catch(err => {
                            console.log(err);
                            res.writeHead(400, "Error in readData");
                            res.end("An error occurred for writeData");
                        });
                        console.log("Success");
                        res.writeHead(200, "Success");
                        res.end("Successful");

                    } else if (req.url == "/readData") {

                        let dataJson = JSON.parse(data);
                        let key = dataJson['key'];
                        console.log("key: " + key);
                        let value = await readData(key).catch(err => {
                            console.log(err);
                            res.writeHead(400, "Error in readData");
                            res.end("An error occurred for readData");
                        });
                        console.log("Read " + value);
                        res.writeHead(200, "Success in readData");
                        res.end(value)

                    } else {

                        console.log("Not supported");
                        res.writeHead(400, "Not supported");
                        res.end("Not supported");
                    }

                } else {

                    console.log("Not supported");
                    res.writeHead(400, "Not supported");
                    res.end("Not supported");
                }

            } catch (err) {

                console.log("An error occurred");
                res.writeHead(400, "An error occurred");
                res.end("Error");

            }
            ;
        });
    } catch (err) {

        console.log("An error occurred");
        res.writeHead(400, "An error occurred");
        res.end("Error");
    }
})

server.listen(1337, config['ip']);
console.log('Server running at http://' + config['ip'] + ':1337');
