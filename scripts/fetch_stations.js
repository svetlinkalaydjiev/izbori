import { chromium } from 'playwright';
import * as cheerio from 'cheerio';
import { writeFileSync, mkdirSync } from 'fs';

const CIK_URL = 'https://www.cik.bg/bg/ns19.04.2026/abroad/registered';
const OUT_FILE = 'data/stations.json';

async function main() {
  console.log(`Launching browser to fetch ${CIK_URL} ...`);

  const browser = await chromium.launch();
  const page = await browser.newPage();

  await page.goto(CIK_URL, { waitUntil: 'load', timeout: 60000 });

  // If Cloudflare challenge is present, wait for it to resolve
  if (await page.title().then(t => t.includes('Just a moment'))) {
    console.log('Cloudflare challenge detected, waiting...');
    await page.waitForFunction(
      () => !document.title.includes('Just a moment'),
      { timeout: 30000 }
    );
  }

  // Wait for page content to be meaningful (САЩ section or any main content)
  await page.waitForSelector('body', { timeout: 10000 });

  const html = await page.content();
  await browser.close();

  console.log(`Fetched ${html.length} bytes.`);

  const result = parseUSAStations(html);
  console.log(`Parsed ${result.stations.length} stations. Total registered: ${result.total}`);

  mkdirSync('data', { recursive: true });
  writeFileSync(OUT_FILE, JSON.stringify(result, null, 2));
  console.log(`Written to ${OUT_FILE}`);
}

function parseUSAStations(html) {
  const $ = cheerio.load(html);

  // Find the element whose own text matches "САЩ (N)"
  let $heading = null;
  $('*').each((_, el) => {
    const $el = $(el);
    const ownText = $el.clone().children().remove().end().text().trim();
    if (/САЩ\s*\(\d+\)/.test(ownText)) {
      $heading = $el;
      return false;
    }
  });

  // Fallback: match full text on small elements
  if (!$heading) {
    $('*').each((_, el) => {
      const $el = $(el);
      if (/САЩ\s*\(\d+\)/.test($el.text()) && $el.children().length <= 2) {
        $heading = $el;
        return false;
      }
    });
  }

  if (!$heading) {
    console.error('Could not find САЩ heading. Dumping first 3000 chars of body:');
    console.error($.html().slice(0, 3000));
    return { updated: new Date().toISOString(), total: null, stations: [] };
  }

  const totalMatch = $heading.text().match(/САЩ\s*\((\d+)\)/);
  const total = totalMatch ? parseInt(totalMatch[1]) : null;
  console.log(`Found heading: <${$heading[0].tagName}> "${$heading.text().trim()}"`);

  // Collect entries after the heading until the next country-level heading
  const stations = [];
  const headingTag = $heading[0].tagName;

  $heading.nextAll().each((_, el) => {
    const $el = $(el);
    if ($el.is(headingTag) && /\(\d+\)/.test($el.text())) return false;

    const leaves = $el.find('*').filter((_, e) => $(e).children().length === 0);
    leaves.each((_, e) => {
      const text = $(e).text().trim();
      if (text) stations.push(text);
    });

    if (leaves.length === 0) {
      const text = $el.text().trim();
      if (text) stations.push(text);
    }
  });

  const unique = [...new Set(stations.filter(Boolean))];
  return { updated: new Date().toISOString(), total, stations: unique };
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
