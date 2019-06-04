const {client} = require('./db');
const puppeteer = require('puppeteer');
const squel = require("squel");
const fs = require('fs');

let fastmarketsKeywords = ['according', 'billion', 'china', 'cobalt', 'companies', 'company', 'copper', 'demand', 'gold', 'lithium', 'market', 'metal', 'metals', 'million', 'mining', 'new', 'price', 'prices', 'production', 'project', 'said', 'steel', 'supply', 'tonne', 'tonnes', 'week', 'world', 'year', 'years'];
let investopediaKeywords = ['Company', 'Brazil', 'Mining', 'Reuters', 'Exchange', 'Tianjin', 'Index', 'Bloomberg', 'Bank', 'Capital', 'Corporation', 'Europe', 'Business', 'Chairman', 'Holdings', 'Shares', 'Trough', 'Black', 'Silver', 'Economics', 'Investment', 'Benchmark', 'Industry', 'Range', 'Congress', 'Journal', 'Year', 'Futures', 'Stock', 'Trade'];
let miningKeywords = ['according', 'australia', 'bhp', 'billion', 'china', 'chinese', 'coal', 'company', 'industry', 'iron', 'market', 'million', 'mining', 'new', 'ore', 'price', 'prices', 'production', 'project', 'resources', 'rio', 'said', 'steel', 'tinto', 'tonne', 'tonnes', 'vale', 'world', 'year', 'years'];

//let fmRe = new RegExp('^' + fastmarketsKeywords.join('$|^') + '$', 'gi');
let fmRe = new RegExp(fastmarketsKeywords.join('|'), 'gimu');
let iRe = new RegExp(investopediaKeywords.join('|'), 'gimu');
let mRe = new RegExp(miningKeywords.join('|'), 'gimu');

async function writeText(text) {
  return fs.writeFileSync("gdelt_results.txt", text, function(err) {
    if(err) { return console.log(err); }
  });
};

function check_matches(text) {
  let fastmarketsMatches = 0;
  let investoPediaMatches = 0;
  let miningMatches = 0;

  text.replace(fmRe, function(match, offset, string){
    fastmarketsMatches +=1;
    return ""
  });

  text.replace(iRe, function(match, offset, string){
    investoPediaMatches +=1;
    return ""
  });

  text.replace(mRe, function(match, offset, string){
    miningMatches +=1;
    return ""
  });
  return [fastmarketsMatches, investoPediaMatches, miningMatches]

};

async function check_news_articles() {
  let query_str = squel.select().from('news').toString();
  console.log(query_str);
  let res = await client.query(query_str);
  let one = [];
  let two = [];
  let three = [];
  for (let row of res.rows) {
    let length = row.full_html.length;
    let matches = check_matches(row.full_html);
    one.push(matches[0]/length);
    two.push(matches[1]/length);
    three.push(matches[2]/length)
  }
  console.log(average(one), standardDeviation(one));
  console.log(average(two), standardDeviation(two));
  console.log(average(three), standardDeviation(three));
  return
}

async function run(){

  //await check_news_articles();
  //let data1 = {'one': [1,2,3], 'two': [2,3,4]};
  //let resp = await writeText(JSON.stringify(data1));
  //let resp = await writeText('jsut some stuff her i guess');
  //console.log(resp);
  //process.exit();

  const browser = await puppeteer.launch({
    headless: false
  });
  const chrome = await browser.newPage();

  let query_str = squel.select().from('gdelt').order('id').toString();
  let res = await client.query(query_str);
  let processed_links = new Set();
  let data = {};
  for (let row of res.rows) {
    if (processed_links.size > 1000) break;
    if (processed_links.size % 50 == 0)  {
      console.log('Processed', processed_links.size);
    }
    if (processed_links.has(row.tolinkurl)) {
      console.log('Already Processed', row.tolinkurl);
      continue;
    }
    processed_links.add(row.tolinkurl);
    try {
      await chrome.goto(row.tolinkurl, {
        waituntil: 'networkidle2',
      });
      let html_str = await chrome.evaluate(() => {
        return document.documentElement.innerHTML;
      });
      let length = html_str.length;
      let matches = check_matches(html_str);
      matches = matches.map(m => m/length);
      console.log('Processed', row.tolinkurl, row.id);
      data[row.tolinkurl] = matches;
    } catch (error) {
      console.log("ERROR", row.tolinkurl);
      continue;
    }
  }
  //console.log(data);
  await writeText(JSON.stringify(data));
  process.exit();
}

function standardDeviation(values){
  var avg = average(values);

  var squareDiffs = values.map(function(value){
    var diff = value - avg;
    var sqrDiff = diff * diff;
    return sqrDiff;
  });

  var avgSquareDiff = average(squareDiffs);

  var stdDev = Math.sqrt(avgSquareDiff);
  return stdDev;
}

function average(data){
  var sum = data.reduce(function(sum, value){
    return sum + value;
  }, 0);

  var avg = sum / data.length;
  return avg;
}


run()