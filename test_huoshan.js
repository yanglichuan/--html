const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  await page.goto('http://localhost:9000/gupiao_new_huoshan.html', { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 3000));
  await browser.close();
})();
