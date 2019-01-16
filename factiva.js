async function checkPages() {
  const browser = await puppeteer.launch({headless: false});
  const page = await browser.newPage();
  //for (var x = 1000; x < 2000; x++) {
  //  console.log('x', x);
  //  //let url = `https://www.reuters.com/news/archive/metals-news?view=page&page=${x}&pageSize=10`;
  //  let url = `https://www.bloomberg.com/search?query=base+metals&endTime=2019-01-09T02:26:52.774Z&page=${x}`
  //  try {
  //    await page.goto(url, {timeout: 3000, waitUntil: 'networkidle2'});
  //  } catch (err) {
  //    console.log('error', err);
  //  }
  //}
  let username = 't0916996';
  let usernameSel = 'body > table:nth-child(2) > tbody > tr:nth-child(3) > td:nth-child(4) > div:nth-child(4) > form > table > tbody > tr:nth-child(2) > td:nth-child(2) > input[type="text"]';
  let password = '1234!@#$qwerQWER';
  let passwordSel = 'body > table:nth-child(2) > tbody > tr:nth-child(3) > td:nth-child(4) > div:nth-child(4) > form > table > tbody > tr:nth-child(3) > td:nth-child(2) > input[type="password"]';
  let nextButton = 'body > table:nth-child(2) > tbody > tr:nth-child(3) > td:nth-child(4) > div:nth-child(4) > form > input[type="submit"]:nth-child(4)';
  let url = 'http://www.lib.nus.edu.sg.libproxy1.nus.edu.sg/eforms/factiva.html';
  await page.goto(url, {timeout: 3000, waitUntil: 'networkidle2'});
  await page.click(usernameSel);
  await page.waitFor(1000);
  await page.keyboard.type(username);
  await page.click(passwordSel);
  await page.keyboard.type(password);
  await page.waitFor(1000);
  await page.click(nextButton);
  console.log('clicked next');
  await page.waitForNavigation();
  console.log('page', page.url());

  //click accept on nus library page
  await page.click('body > table:nth-child(2) > tbody > tr:nth-child(3) > td:nth-child(4) > div > form > input[type="submit"]:nth-child(2)');
  await page.waitForNavigation();
  console.log('page', page.url());

  //click accept on factiva page
  await page.click('body > div > table > tbody > tr:nth-child(2) > td > font > div > table > tbody > tr > td > p > a > img');
  await page.waitForNavigation();
  console.log('page', page.url());

  //click search
  await page.click('#navmbm0 > ul > li:nth-child(1) > a');

  //// on search page now
  //await page.waitForNavigation();
  //await page.click('#nsTab > div.pnlTabArrow');
  //await page.waitFor(1000);
  //await page.click('#nsMnu > ul > li:nth-child(1) > span')


}

checkPages();
