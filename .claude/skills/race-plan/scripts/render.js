// node render.js page.html out.png [width=1080] [scale=2]  -> full-height PNG
const { chromium } = require('playwright');
(async () => {
  const [,, html, out, w, s] = process.argv;
  const W = Number(w || 1080), scale = Number(s || 2);
  const b = await chromium.launch();
  const p = await (await b.newContext({ viewport: { width: W, height: 800 }, deviceScaleFactor: scale })).newPage();
  await p.goto('file://' + require('path').resolve(html));
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  const H = Math.ceil(await p.evaluate(() => document.body.scrollHeight));
  await p.setViewportSize({ width: W, height: H });
  await p.screenshot({ path: out, clip: { x: 0, y: 0, width: W, height: H } });
  console.log(`${out} ${W * scale}x${H * scale}`);
  await b.close();
})();
