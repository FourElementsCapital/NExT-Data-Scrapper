const squel = require("squel");
const { Pool, Client } = require('pg');

let client;

if (process.env.NODE_ENV == 'development') {
  console.log('Running in Development'); 
  client = new Client({
    user: "scrappyuser",
    database: "scrappy",
    password: "password",
    port: 5433
  });
} else if (process.env.NODE_ENV == 'production') {
  console.log('Running in Production');
  client = new Client({
    user: "scrappyuser",
    database: "scrappy",
    password: "aiapaiap",
    port: 5432
  });
} else {
  throw "Node Environment Not Set"
}

client.connect();

module.exports = {
  client: client
};


