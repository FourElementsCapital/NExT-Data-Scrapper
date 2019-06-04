const puppeteer = require('puppeteer');
const createCsvWriter = require('csv-writer').createArrayCsvWriter;
var _ = require('lodash');
const csvWriter = createCsvWriter({
  path: 'words.csv',
  append: true
});

SITE = 'https://www.investopedia.com/terms/';
LETTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
  'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'];
terms = [];

async function checkNext(chrome) {
  let href = await chrome.evaluate(sel => {
    var href = document.querySelector(sel) ? true : false;
    return href;
  }, '.next a' );
  console.log('checknext', href); 
  return href
}


const fs = require('fs');
function writeText(text) {
  fs.writeFile("terms.txt", text, function(err) {
    if(err) { return console.log(err); }
  });
};


async function scrapePage(chrome, url) {

}


async function run() {

  const browser = await puppeteer.launch({
    headless: false
  });
  const chrome = await browser.newPage();

    for (letter of LETTERS) {
      console.log("Processing", letter);
      let page = 0;
      do {
        await chrome.goto(`${SITE}/${letter}/?page=${page}`, {waitUntil: 'networkidle2'});
        page += 1;
        let nodes = await chrome.evaluate((sel) => {
          let nodes = Array.from(document.querySelectorAll(sel));
          nodes = nodes.map(n => n.innerHTML.trim());
          return nodes;
        },'.item-title a');
        terms.push(nodes)
      } while (await checkNext(chrome));
    }

  //console.log('terms', terms);
  terms = _.flatten(terms);
  //console.log('terms', terms);
  writeText(terms);
}

run();


