const squel = require("squel");
//const { Pool, Client } = require('pg');
const mariadb = require('mariadb');

//let client;

if (process.env.NODE_ENV == 'development') {
  console.log('Running in Development'); 
  pool = mariadb.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    database: process.env_DB_NAME,
    password: process.env.DB_PASS,
    port: process.env.DB_PORT,
    connectionLimit: 10
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

pool.getConnection()
    .then(conn => {
      console.log("connected ! connection id is " + conn.threadId);
      conn.release(); //release to pool
    })
    .catch(err => {
      console.log("not connected due to error: " + err);
    });

module.exports = pool;
//module.exports = {
//  client: client
//};

