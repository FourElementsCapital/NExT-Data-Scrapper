const puppeteer = require('puppeteer');
const squel = require("squel");
const moment = require('moment');
const { Pool, Client } = require('pg');
const chrono = require('chrono-node');

const startPoints = [
  {
    url: 'http://www.mining.com/tag/copper/',
    source: 'mining-copper',
    last_page: 314,
  },
  {
    url: 'http://www.mining.com/tag/iron-ore/',
    source: 'mining-iron',
    last_page: 189,
  }
];


const client = new Client({
  user: "scrappyuser",
  database: "scrappy",
  password: "password",
  port: 5433
});

client.connect();

async function getLinks(metal, page, page_no) {
  await page.goto(
      `${metal.url}page/${page_no}`,
      {waitUntil: 'networkidle2'}
  );
  await page.waitForSelector('.page-title');
  const links = await page.evaluate(() => {
    let link_nodes = Array.from(document.querySelectorAll('.archive-post h3 a'));
    return link_nodes.map(link => link.href)
  });

  return links
}


function parseDate(dateStr) {

  let date = moment(dateStr, 'MMM. D, YYYY, h:mm a', true);
  if (date.isValid()) {
    return {date: date.format('YYYY-MM-DD'), time: date.format('H:mm')}
  }
  date = chrono.parseDate(dateStr);
  if (date.toString() != 'Invalid Date') {
    let m = moment(date);
    return {date: m.format('YYYY-MM-DD'), time: m.format('H:mm')}
  }
  throw `Error parsing date: ${dateStr}`

}

async function get_article_data(link, page, metal) {
  await page.goto(link, {waituntil: 'networkidle2'});

  let news_id = link.split('/').filter(x => x).slice(2).join("-");

  let article = {
    original_url: link,
    source: metal.source,
    news_id: news_id
  };

  var selectors = {
    title: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.post-details > h2',
    author: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.post-details > div.post-byline > a',
    datetime: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.post-details > div.post-byline > time',
    full_text: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.the-post',
    full_html: 'body'
  };

  try {
    let article_data = await Promise.all(Object.keys(selectors).map(key => {
      let sel = selectors[key];
      return page.$eval(sel, ele => ele ? ele.innerHTML : null)
    }));
    article.title = article_data[0];
    article.author = article_data[1];
    let {date, time} = parseDate(article_data[2]);
    article.date = date;
    article.time = time;
    article.full_text = article_data[3];
    article.full_html = article_data[4];
    return article;

  } catch (error) {
    console.log('error', error);
    return false

  }

}

async function save_article(article) {
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
async function run() {

  const browser = await puppeteer.launch({
    headless: false
  });
  const page = await browser.newPage();

  //let startPoint = startPoints[1];
  //console.log("++++++++++++++++++++++++++++++++++++++++++++++++");
  //console.log('scraping', startPoint.source);
  //console.log("++++++++++++++++++++++++++++++++++++++++++++++++");
  //for (var page_no = 1; page_no <= startPoint.last_page; page_no++) {
  //  console.log('scraping page', page_no);
  //  let links = await getLinks(startPoints[0], page, page_no);
  //  let article = true;
  //
  //  for (link of links) {
  //    console.log('processing link', link);
  //    try {
  //      article = await get_article_data(link, page, startPoint);
  //    } catch (error) {
  //      console.log('error getting article data', link);
  //      article = false;
  //    }
  //    if (article) await save_article(article);
  //    else {
  //      console.log('could not save link', link);
  //    }
  //  }
  //}

  let url = 'http://www.mining.com/web/minings-biggest-jobs-grabs-contenders/';
  let article = await get_article_data(url, page, startPoints[1]);
  let resp = await save_article(article);
  console.log('resp', resp);
  console.log('article', article);

  await client.end();
  await browser.close()

}

run();