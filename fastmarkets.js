const puppeteer = require('puppeteer');
const squel = require("squel");
const { Pool, Client } = require('pg');


// (Copper, Nickel, Tin, Aluminum, Lead and Zinc)

const client = new Client({
  user: "scrappyuser",
  database: "scrappy",
  password: "password",
  port: 5433
});

client.connect();

let HEADLESS = true;
let baseURL = 'https://www.fastmarkets.com';

async function getLinks(page) {
  const item_selector = '#main > section > ol > li:nth-child(INDEX) > article > div.mediaItem-body > header > a';
  const link_count = await page.$$eval('.mediaItem-header', headers => headers.length);

  const links = new Array(link_count).fill(0).map((item, index) => {
    let sel = item_selector.replace('INDEX', index + 1);
    return page.$eval(sel, e => {
      return e ? e.getAttribute('href') : null
    });
  });

  const results = await Promise.all(links);
  return results
}

async function getArticle(page, link) {
  await page.goto(`${baseURL}${link}`);

  let news_id = link.split('/')[2]
  console.log('processing:', link);
  let article = {
    news_id: news_id,
    source: 'fastmarkets'
  };

  let dateSel = '#main > article > div.article-intro > div > div.articleMeta-publication > time > span.date';
  var descSel = '#main > article > div.article-intro > p';
  var titleSel = '#main > article > header > h1 > span';
  var authorSel = '#main > article > div.article-intro > div > div.articleMeta-publication > div > ul > li > a';
  var fullTextSel = '#main > article > div.article-body';
  var selectors = {
    title: titleSel,
    description: descSel,
    author: authorSel,
    date: dateSel,
    full_text: fullTextSel
  };
  try {
    var articleValues = await Promise.all(Object.keys(selectors).map(key => {
      let sel = selectors[key];
      return page.$eval(sel, ele => {
        return ele ? ele.innerHTML : null
      })
    }));
  } catch (error){
    console.log("+++++++++++++Could not process");
    return false
  }

  return Object.keys(selectors).reduce((obj, c, i) => {
    obj[c] = articleValues[i];
    return obj
  }, article);

}

async function add_to_database(article) {
  let query_str = squel.insert({replaceSingleQuotes: true})
      .into('news')
      .setFields(article)
      .toString();
  query_str += ' ON CONFLICT (news_id) DO NOTHING';
  return new Promise((resolve, reject) => {
    client.query(query_str, (err, res) => {
      if (err) {
        reject(err);
      } else {
        resolve(res)
      }
    });
  });

}

async function process_article(page, link) {
  let article = await getArticle(page, link);
  if (!article) return;
  try {
    let resp = await add_to_database(article);
  } catch (error) {
    console.log('error', error);
    console.log('article', article);
  }
}


async function process_article_list(page, page_no) {

  await page.goto(
      `${baseURL}/commodities/base-metals/news/${page_no}`,
      {waitUntil: 'networkidle2'}
  );

  var links = await getLinks(page);

  for (var link of links) {
    await process_article(page, link)
  }


}


async function run() {

  const browser = await puppeteer.launch({
    headless: false
  });
  const page = await browser.newPage();

  for (var p = 1; p <= 2; p ++) {
    await process_article_list(page, p)
  }

  return await browser.close();

}

run();
//client.end();

