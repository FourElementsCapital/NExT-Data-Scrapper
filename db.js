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
}


//query_str = squel.insert().into('news').setFields( articles[0] ).toString();
//query_str += ' ON CONFLICT (news_id) DO NOTHING';
//console.log('query', query_str);
//
//client.query(query_str, (err, res) => {
//  if (err) {
//    console.log(err.stack)
//  } else {
//    console.log('res', res);
//  }
//  client.end();
//  process.exit();
//});
//
////client.query('select * from news;', (err, res) => {
////  console.log(err, res);
////  client.end();
////  process.exit();
////})
//
//
//// more general structure for scraping
//// get article (config_obj, url, overwrite=false/true)
//// config object has all details about how to
//
//// save_article(article)
//// pretty obvious
//
//// get links (url, config obj)
//// config should be same as earlier.
//// but requies passing object around.
//
//// run function should take in the config object
//// and done. seems like a feasible way to make it work.
//// refactor to make this work
//
//// how about for non paginated sources that require some other format?
//// some sites have the scroll to the bottom thing going on.
//// config objects can be pretty complicated i guess.
//// hmm.
//

/*

The structure i came up with is so ugly. I want a better architecture.

// The idea is to be able to just write new site configs when you want to scrape a new site. that's a good starting point for what you want.

// why the article and config split.

 */

////
