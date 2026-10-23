#!/usr/bin/env node
// Record a walkthrough video of an animated essay and run the layout checks.
// Usage: node qa_record.cjs <essay.html> <out-dir> [seconds-per-figure=12]
// Needs playwright-core (or playwright) with a Chromium build; set PLAYWRIGHT_CORE=/path/to/playwright-core if it is not resolvable.
// ffmpeg is optional; with it, contact sheets (2 s per frame, 3x3) are written next to the video.
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const [file, outDir, secsArg] = process.argv.slice(2);
if (!file || !outDir) { console.error('usage: node qa_record.cjs <essay.html> <out-dir> [seconds-per-figure]'); process.exit(2); }
const secs = +(secsArg || 12);
let pw; for (const m of [process.env.PLAYWRIGHT_CORE, 'playwright-core', 'playwright'].filter(Boolean)) { try { pw = require(m); break; } catch {} }
if (!pw) { console.error('playwright-core not found: npm i -g playwright-core && npx playwright install chromium, or set PLAYWRIGHT_CORE'); process.exit(2); }
const url = 'file://' + path.resolve(file);
fs.mkdirSync(outDir, { recursive: true });
(async () => {
  const b = await pw.chromium.launch(); const errors = [];
  const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, recordVideo: { dir: outDir, size: { width: 1440, height: 900 } } });
  const p = await ctx.newPage();
  p.on('pageerror', e => errors.push('pageerror: ' + e.message)); p.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await p.goto(url); await p.waitForTimeout(secs * 500);
  const figs = await p.$$('.fig');
  for (let i = 0; i < figs.length; i++) {
    await figs[i].evaluate(e => window.scrollTo(0, e.getBoundingClientRect().top + scrollY - 110));
    await p.waitForTimeout(secs * 1000);
    const box = await figs[i].$('input[type=checkbox]');
    if (box) { await box.click(); await p.waitForTimeout(secs * 700); }
    await figs[i].screenshot({ path: path.join(outDir, `fig-${String(i + 1).padStart(2, '0')}.png`) });
  }
  const video = await p.video().path(); await ctx.close();
  const final = path.join(outDir, 'walkthrough.webm'); fs.renameSync(video, final);
  const ph = await b.newPage({ viewport: { width: 400, height: 900 }, reducedMotion: 'reduce' });
  await ph.goto(url); await ph.waitForTimeout(500);
  const phone = await ph.evaluate(() => ({ scrollWidth: document.documentElement.scrollWidth,
    offenders: [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > 401 && !e.ownerSVGElement && !e.closest('.stage,.tw,.phases')).slice(0, 8).map(e => e.tagName + ' ' + (e.textContent || '').trim().slice(0, 40)) }));
  await ph.screenshot({ path: path.join(outDir, 'phone.png') });
  const dk = await b.newPage({ viewport: { width: 1440, height: 900 }, colorScheme: 'dark', reducedMotion: 'reduce' });
  await dk.goto(url); await dk.waitForTimeout(500); await dk.screenshot({ path: path.join(outDir, 'dark.png') });
  await b.close();
  let sheets = [];
  try { execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', final, '-vf', 'fps=1/2,scale=720:-1,tile=3x3', path.join(outDir, 'sheet%02d.png')]); sheets = fs.readdirSync(outDir).filter(f => f.startsWith('sheet')); } catch { sheets = ['(ffmpeg unavailable: no contact sheets)']; }
  const report = { file: path.resolve(file), figures: figs.length, video: final, errors, phone, sheets, pass: errors.length === 0 && phone.scrollWidth <= 400 };
  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2)); process.exit(report.pass ? 0 : 1);
})();
