let {MiningCopper, FastMarkets} = require('./article');

let mining_copper = {
    name: "Mining.com - Copper",
    page_url: function (page_no) {
      return `http://www.mining.com/tag/copper/page/${page_no}`;
    },
    link_selector: '.archive-post h3 a',
    last_page: 314,
    article_wrapper: MiningCopper
}

let fastmarkets = {
  name: 'fastmarkets',
  page_url: function(page_no) {
    return `https://www.fastmarkets.com/commodities/base-metals/news/${page_no}`;
  },
  link_selector: '.mediaItem-body a',
  last_page: 1
}




module.exports = {
  mining_copper: mining_copper,
  fastmarkets: fastmarkets
}
;