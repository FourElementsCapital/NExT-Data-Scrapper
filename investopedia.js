const puppeteer = require('puppeteer');
const createCsvWriter = require('csv-writer').createArrayCsvWriter;
const csvWriter = createCsvWriter({
  path: 'words.csv',
  append: true
});

SITE = 'https://www.investopedia.com/terms/';
LETTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'];

async function checkNext(chrome) {
  await chrome.evaluate(sel => {
    var href = document.querySelector(sel).href;
    return href
  }, '.next>a' )
}

async function run() {
  const browser = await puppeteer.launch({
    headless: false
  });
  const chrome = await browser.newPage();

  await chrome.goto(`${SITE}/${LETTERS[0]}`, {waitUntil: 'networkidle2'});

  //var words = await chrome.evaluate(sel => {
  //  let nodes = Array.from(document.querySelectorAll('h3.item-title a'));
  //  return nodes.map(node => [node.innerText])
  //}, 'h3.item-title a');

  var next = await checkNext(chrome);
  console.log(next);



  //await csvWriter.writeRecords(words);

}

run()


