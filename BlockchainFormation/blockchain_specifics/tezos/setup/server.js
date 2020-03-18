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
const tezos = require('./tezos.js');
const tezos_client = new tezos();

const config = require('./config.json');


async function writeData(value, from, to) {

    await tezos_client.writeData(value, from, to).catch (err => {
        console.log(err);
        throw("Error");
    });
    return "1";
}

async function readData(account) {

    let response = await tezos_client.readData(account).catch (err => {
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
                        let value = dataJson['value'];
                        let from = dataJson['from'];
                        let to = dataJson['to']
                        console.log("value: " + value);
                        console.log("from: " + from);
                        console.log("to: " + to);

                        await writeData(value, from, to).catch(err => {
                            console.log(err);
                            res.writeHead(400, "Error in readData");
                            res.end("An error occurred for writeData");
                        });
                        console.log("Success");
                        res.writeHead(200, "Success");
                        res.end("Successful");

                    } else if (req.url == "/readData") {

                        let dataJson = JSON.parse(data);
                        let account = dataJson['account'];
                        console.log("account: " + account);
                        let value = await readData(account).catch(err => {
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
                console.log(err);
                res.writeHead(400, "An error occurred");
                res.end("Error");

            };
        });
    } catch (err) {

        console.log(err);
        res.writeHead(400, "An error occurred");
        res.end("Error");
    }
})

server.listen(1337, config.ip);
console.log('Server running at http://' + config['ip'] + ':1337');
