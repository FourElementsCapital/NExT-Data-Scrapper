//let {MiningCopper, FastMarkets} = require('./article');


let mining_general = {
  name: "Mining.com - General",
  page_url: function (page_no) {
    return `https://www.mining.com/markets/${page_no}/`;
  },
  link_selector: 'div.row h1 a, div.row h3 a, article.row.pb-3 h1 a, article.row.pb-3 h3 a',
  last_page: 50,

};

let mining_copper = {
  name: "Mining.com - Copper",
  page_url: function (page_no) {
    return `https://www.mining.com/commodity/copper/?page=${page_no}`;
  },
  link_selector: 'div.row h1 a, div.row h3 a, article.row.pb-3 h1 a, article.row.pb-3 h3 a',
  last_page: 50,
};

let mining_nickel = {
  name: "Mining.com - Nickel",
  page_url: function (page_no) {
    return `https://www.mining.com/commodity/nickel/?page=${page_no}`;
  },
  link_selector: 'div.row h1 a, div.row h3 a, article.row.pb-3 h1 a, article.row.pb-3 h3 a',
  last_page: 50,
};
let mining_zinc = {
  name: "Mining.com - Zinc",
  page_url: function (page_no) {
    return `https://www.mining.com/commodity/zinc/?page=${page_no}`;
  },
  link_selector: 'div.row h1 a, div.row h3 a, article.row.pb-3 h1 a, article.row.pb-3 h3 a',
  last_page: 50,
};

let fastmarkets = {
  name: 'fastmarkets',
  page_url: function (page_no) {
    return `https://www.fastmarkets.com/commodities/base-metals/news/${page_no}`;
  },
  link_selector: '.mediaItem-body a',
  last_page: 100
};


module.exports = {
  mining_general: mining_general,
  mining_copper: mining_copper,
  mining_nickel: mining_nickel,
  mining_zinc: mining_zinc,
  fastmarkets: fastmarkets
}
;
