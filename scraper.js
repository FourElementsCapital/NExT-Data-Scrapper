const puppeteer = require('puppeteer');
const squel = require("squel");
const moment = require('moment');
//const { Pool, Client } = require('pg');
const mariadb = require('mariadb');
const chrono = require('chrono-node');
const site_configs = require('./site_configs');
const client = require('./db');
extractor = require('unfluff');

async function getLinks(link, chrome) {
  chrome.setExtraHTTPHeaders({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
  });

  await chrome.goto(
      link,
      {waitUntil: 'networkidle2'}
  );
  return await chrome.evaluate(sel=> {
    let link_nodes =  Array.from(
        document.querySelectorAll(sel)
    );
    return link_nodes.map(link => link.href);
  }, global.site.link_selector);
}

async function get_article_data(link, chrome) {
  chrome.setExtraHTTPHeaders({
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'
  });
  await chrome.goto(link, {waituntil: 'networkidle2'});

  let Article = global.site.article_wrapper;
  let selectors = Article.selectors();
  let container = {original_url: link};

  try {
    let keys = Object.keys(selectors);
    let article_data = await Promise.all(Object.keys(selectors).map(key => {
      let sel = selectors[key];
      return chrome.$eval(sel, ele => ele ? ele.innerHTML : "");
    }));
    keys.forEach((key, index) => {
      container[key] = article_data[index]
    });
    return new Article(container);

  } catch (error) {
    console.log('error', error); 
    return false
  }
}


async function save_to_db(source, html, url) {
  let query_str = squel.insert({replaceSingleQuotes: true})
      .into('scraperDb.news')
      .setFields({
        source: source,
        full_html: html,
        original_url: url
      }).toString();
  query_str += ' ON DUPLICATE KEY UPDATE `source`=VALUES(`source`),`full_html`=VALUES(`full_html`),`original_url`=VALUES(`original_url`)';
  //console.log(query_str)
  return new Promise((resolve, reject) => {
    client.query(query_str)
          .then(res => {
                console.log(res)
                resolve(res);
          })
          .catch(err => {
                 reject(err)
          })
  });
}


async function run() {
  global.site = site_configs[process.argv[2]];
  console.log('site', site);
  global.start_page = 1;
  if (!site) { throw "Unrecognized Site" }
  const browser = await puppeteer.launch({
    headless: process.env.NODE_ENV == 'production'
  });
  const chrome = await browser.newPage();

  console.log("++++++++++++++++++++++++++++++++++++++++++++++++");
  console.log('Scraping', site.name);
  console.log("++++++++++++++++++++++++++++++++++++++++++++++++");
  for (let page_no = 1; page_no <= site.last_page; page_no++) {

    console.log('Scraping Page', page_no)
    let links = await getLinks(site.page_url(page_no), chrome);

    for (let link of links) {
      try {
        await chrome.goto(link, {waituntil: 'networkidle2'});
        let html_str = await chrome.evaluate(() => {
          return document.documentElement.innerHTML
        });
        let resp = await save_to_db(site.name, html_str, link);
      } catch (error) {
        console.log('error', error)
      }
    }
  }
  await browser.close()
  process.exit();
}


run();
