## Overview

This repo has code for 3 main functions.

1. Historical scraping of news sites 
2. Monitoring news sites for changes in real time 
3. Scraping investopedia's financial dictionary 

Puppeteer, a node library is used to run headless chrome to access and save web pages.

Full html dumps of webpages are stored in a PostgreSQL database.

### Installation

Requirements: Node v8.9.0 or higher.

1. Clone repo and install requirements by running 'npm install' 
2. Set an environment variable named 'NODE_ENV' to either 'production' or 'development'. In production, chrome runs in headless mode. 
3. Set up the database.&nbsp;This project uses a PostgreSQL instance&nbsp;with&nbsp;a single database and a single table named 'news' 

A dump of the database schema can be found in 'news.schema'. The fields, types and constraints can be found in 'news_table_fields.txt' In db.js, change the values of user, database, password and port to the correct values for your database.

### Historical Scraping

Start scraping by runing 'node scraper.js <<site_config_name>>'. e.g. 'node scraper.js mining_general'


Each site to be scraped needs a config object that is stored in 'site_configs.js'.


Example config for scraping mining.com's front page.

```
let mining_general = {

 let mining_general = { 
 &nbsp;name: "Mining.com - General",
  page_url: function (page_no) {
    return `[http://www.mining.com/page/${page_no}` http://www.mining.com/page/${page_no}`];
  },
  link_selector: '.kesselPost h3 a',
  last_page: 2200,
 }
 
```


link_selector refers to the the CSS selector that corresponds to each article in the list of articles.

== Live Monitoring of News Sites ==

Start monitoring by running 'node live_polling.js'

'live_polling.js' has an object 'CONF' that has data about which sites are being monitored for changes.

The variable 'POLL_INTERVAL', (currently set to 30 seconds), controls how often sites are checked.

Live polling also logs results to the alphien chat room "News articles". Currently Deepan's credentials are being used to send the messages, but this can be changed to any&nbsp;other user if desired.&nbsp;

&nbsp;

### Investopedia Financial Dictionary

Start scraping investopedia by running 'node investopedia.js'

The script stores results in an array and write results to a file 'terms.txt' once it finishes.&nbsp;

&nbsp;

&nbsp;

&nbsp;


