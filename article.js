const moment = require('moment');
const chrono = require('chrono-node');
const {client} = require('./db');
const squel = require("squel");

global.client = client;

class Article {
  constructor(obj) {
    Object.assign(this, obj)
  }

  async save_to_db(update = false) {
    let query_str = squel.insert({replaceSingleQuotes: true})
        .into('news')
        .setFields(this)
        .toString();
    query_str += ' ON CONFLICT (news_id) DO NOTHING';
    return new Promise((resolve, reject) => {
      global.client.query(query_str, (err, res) => {
        if (err) reject(err);
        else resolve(res)
      });
    });
  }

}

class FastMarkets extends Article {
  constructor(obj) {
    super(obj);
  }
}

class MiningCopper extends Article {
  static selectors() {
    return {
      title: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.post-details > h2',
      author: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.post-details > div.post-byline > a',
      datetime: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.post-details > div.post-byline > time',
      full_text: 'body > div.container > div.kesselBody > div > div.col-xs-12.mainBody > div > div.post-content > div.the-post',
      full_html: 'body'
    }
  }

  constructor(obj) {
    super(obj);
    this.news_id = this.original_url.split('/').filter(x => x).slice(2).join("-");
    this.source = 'mining-copper';
    this.datetime = obj.datetime;
  }

  set datetime(value) {
    let res = this.parseDate(value);
    this.date = res.date;
    this.time = res.time
  }

  static link_selector(document) {
    let link_nodes = Array.from(
        document.querySelectorAll('.archive-post h3 a')
    );
    return link_nodes.map(link => link.href)
  }

  parseDate(dateStr) {
    let date = moment(dateStr, 'MMM. D, YYYY, h:mm a', true);
    if (date.isValid()) return {date: date.format('YYYY-MM-DD'), time: date.format('H:mm')}
    date = chrono.parseDate(dateStr);
    if (date.toString() != 'Invalid Date') {
      let m = moment(date);
      return {date: m.format('YYYY-MM-DD'), time: m.format('H:mm')}
    }
    throw `Error parsing date: ${dateStr}`
  }

  save_to_db(update = false) {
    super.save_to_db(update)
  }
}


module.exports = {
  MiningCopper: MiningCopper,
  FastMarkets: FastMarkets
};
