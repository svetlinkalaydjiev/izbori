import * as cheerio from 'cheerio';
import { writeFileSync, mkdirSync } from 'fs';

const CIK_URL = 'https://www.cik.bg/bg/ns19.04.2026/abroad/registered';
const OUT_FILE = 'data/stations.json';

async function main() {
  console.log(`Fetching ${CIK_URL} ...`);

  const res = await fetch(CIK_URL, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'bg,en-US;q=0.9,en;q=0.8',
    }
  });

  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  const html = await res.text();
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
    // Check own text only (not inherited from children) to avoid matching ancestors
    const ownText = $el.clone().children().remove().end().text().trim();
    if (/САЩ\s*\(\d+\)/.test(ownText)) {
      $heading = $el;
      return false; // break
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
    // Stop at the next country heading (same tag, contains "(N)")
    if ($el.is(headingTag) && /\(\d+\)/.test($el.text())) return false;

    // Collect all non-empty leaf text nodes
    const leaves = $el.find('*').filter((_, e) => $(e).children().length === 0);
    leaves.each((_, e) => {
      const text = $(e).text().trim();
      if (text) stations.push(text);
    });

    // If no leaves, use the element's own text
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
