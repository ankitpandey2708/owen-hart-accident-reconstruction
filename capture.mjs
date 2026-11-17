// node capture.mjs <scene> <seconds> [fps] [onlyFrame]
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import puppeteer from 'puppeteer-core';

const [scene, secs, fpsArg, only] = process.argv.slice(2);
const FPS = Number(fpsArg || 30);
const root = path.resolve('.');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' };
const server = http.createServer((req, res) => {
  const p = path.join(root, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(root) || !fs.existsSync(p)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
}).listen(0, '127.0.0.1');
await new Promise(r => server.on('listening', r));
const port = server.address().port;

const browser = await puppeteer.launch({
  executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  headless: true, args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist', '--hide-scrollbars'],
});
const page = await browser.newPage();
page.on('console', m => console.log('PAGE:', m.text()));
page.on('pageerror', e => console.log('PAGEERR:', e.message));
await page.setViewport({ width: 1920, height: 1080 });
const file = ['s4','s7'].includes(scene) ? 'scene.html' : 'cards.html';
await page.goto(`http://127.0.0.1:${port}/threejs/${file}?scene=${scene}`);
await page.waitForFunction('window.ready === true', { timeout: 30000 });
const out = path.join('frames', scene); fs.mkdirSync(out, { recursive: true });
const N = Math.round(Number(secs) * FPS);
const frames = only !== undefined ? only.split(',').map(Number) : [...Array(N).keys()];
for (const f of frames) {
  await page.evaluate(t => window.renderAt(t), f / FPS);
  await page.screenshot({ path: path.join(out, String(f).padStart(4, '0') + '.png'), omitBackground: scene === 'hud5' });
  if (f % 150 === 0) console.log(scene, f, '/', N);
}
await browser.close(); server.close();
