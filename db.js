const squel = require("squel");
const { Pool, Client } = require('pg');

let client;

if (process.env.NODE_ENV == 'development') {
  console.log('Running in Development'); 
  client = new Client({
    user: process.env.DB_USER,
    database: process.env.DB_HOST,
    password: process.env.DB_PASS,
    port: process.env.DB_PORT
  });
} else if (process.env.NODE_ENV == 'production') {
  console.log('Running in Production');
  client = new Client({
    user: process.env.DB_USER,
    database: process.env.DB_HOST,
    password: process.env.DB_PASS,
    port: process.env.DB_PORT
  });
} else {
  throw "Node Environment Not Set"
}

client.connect();

module.exports = {
  client: client
};


