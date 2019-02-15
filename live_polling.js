const puppeteer = require('puppeteer');
const {client} = require('./db');
const squel = require("squel");
const moment = require('moment');


let POLL_INTERVAL = 30000;

let CONF = {
  reuters: {
    name: 'reuters',
    url: "https://www.reuters.com/finance/commodities",
    selector: ".featured-article a",
    last_article: null
  },
  fastmarkets: {
    name: 'fastmarkets',
    url:"https://www.fastmarkets.com/commodities/base-metals/news/1",
    selector: '.mediaItem-body a',
    last_article: null
  },
  mining_copper: {
    name: 'mining_copper',
    url: 'http://www.mining.com/tag/copper/',
    selector: '.archive-post a',
    last_article: null
  },
  mining_iron: {
    name: 'mining_iron',
    url: 'http://www.mining.com/tag/iron-ore/',
    selector: '.archive-post a',
    last_article: null
  },
  mining_nickel: {
    name: 'mining_iron',
    url: 'http://www.mining.com/tag/nickel/',
    selector: '.archive-post a',
    last_article: null
  }
}

async function save_article(tab, url, conf) {
  await tab.goto(url, {waitUntil: 'domcontentloaded'});

  let full_html = await tab.evaluate(() => {
    return document.documentElement.innerHTML;
  });

  let query_str = squel.insert({replaceSingleQuotes: true})
      .into('news')
      .setFields({
        original_url: url,
        full_html: full_html,
        source: conf.name,
        article_timestamp: moment.utc().format()
      })
      .toString();
  query_str += ' ON CONFLICT (original_url) DO NOTHING';
  return new Promise((resolve, reject) => {
    client.query(query_str, (err, res) => {
      if (err) reject(err);
      else resolve(res)
    });
  });

}

async function checkPage(tab, conf) {
  console.log('running check', conf.name);
  tab.setExtraHTTPHeaders({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
  });
  try {
    await tab.goto(conf.url, {waitUntil: 'domcontentloaded'});

    let latest_article = await tab.evaluate(function(sel) {
      let node =  document.querySelector(sel);
      return node ? node.href : "Empty"
    }, conf.selector);
    if (latest_article == 'Empty') {
      let html = await tab.evaluate(function(sel){
        return document.documentElement.innerHTML
      })
      console.log('full html', html);
    }
    else if (conf.last_article !== latest_article) {
      console.log('ARTICLE CHANGED!!!!!!', latest_article, conf.name);
      await save_article(tab, latest_article, conf);
      conf.last_article = latest_article;
    }
    return latest_article;
  } catch (E) {
    console.log('ERORRRRRRRRR', E, conf.name);
  } finally {
    setTimeout(checkPage.bind(this, tab, conf), POLL_INTERVAL);
  }
}

async function run() {

  const browser = await puppeteer.launch({
    headless: false
  });

  //for (site in CONF) {
  //  let tab = await browser.newPage();
  //  checkPage(tab, CONF[site]);
  //}

  //const reutersTab = await browser.newPage();
  const fastMarketsTab = await browser.newPage();
  //const mining_copper = await browser.newPage();
  //const mining_iron = await browser.newPage();
  //const mining_nickel = await browser.newPage();
  //
  //
  //checkPage(reutersTab, CONF.reuters);
  checkPage(fastMarketsTab, CONF.fastmarkets);
  //checkPage(mining_copper, CONF.mining_copper);
  //checkPage(mining_iron, CONF.mining_iron);
  //checkPage(mining_nickel, CONF.mining_nickel);
}

run();
