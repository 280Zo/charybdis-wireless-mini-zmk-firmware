const fs = require('fs');
const { chromium } = require('playwright');

const templatePath = 'keymap-drawer/stacked/composite-template.html';
const stackedSvgPath = 'keymap-drawer/stacked/stacked.svg';
const combosSvgPath = 'keymap-drawer/stacked/combos.svg';
const legendSvgPath = 'keymap-drawer/stacked/legend.svg';
const outputPngPath = 'keymap-drawer/stacked/stacked-combos.png';

const bg = process.env.KEYMAP_BG || '#2F4858';
const gap = Number.parseInt(process.env.KEYMAP_GAP || '0', 10);
const margin = Number.parseInt(process.env.KEYMAP_MARGIN || '20', 10);
const scale = Number.parseFloat(process.env.KEYMAP_SCALE || '2');
const hinting = process.env.KEYMAP_HINTING || 'medium';
const legendOn = (process.env.KEYMAP_LEGEND || '1') !== '0';
const stackedTrimBottom = Number.parseInt(process.env.KEYMAP_STACKED_TRIM_BOTTOM || '-71', 10);
const legendTrimTop = Number.parseInt(process.env.KEYMAP_LEGEND_TRIM_TOP || '-58', 10);
const legendTrimBottom = Number.parseInt(process.env.KEYMAP_LEGEND_TRIM_BOTTOM || '-58', 10);
const combosTrimTop = Number.parseInt(process.env.KEYMAP_COMBOS_TRIM_TOP || '-60', 10);

const toDataUrl = (svgPath) => {
  const svg = fs.readFileSync(svgPath, 'utf8');
  return `data:image/svg+xml;base64,${Buffer.from(svg, 'utf8').toString('base64')}`;
};

const stackedSrc = toDataUrl(stackedSvgPath);
const combosSrc = toDataUrl(combosSvgPath);
const legendSrc = legendOn ? toDataUrl(legendSvgPath) : '';

const legendBlock = legendOn
  ? '<div class="block"><img id="legend-svg" src="__LEGEND_SRC__" alt="legend key" /></div>'
  : '';

let html = fs.readFileSync(templatePath, 'utf8');
html = html.replaceAll('__KEYMAP_BG__', bg);
html = html.replaceAll('__KEYMAP_GAP__', String(Number.isFinite(gap) ? gap : 0));
html = html.replaceAll('__KEYMAP_MARGIN__', String(Number.isFinite(margin) ? margin : 20));
html = html.replaceAll('__STACKED_SRC__', stackedSrc);
html = html.replaceAll('__COMBOS_SRC__', combosSrc);
html = html.replace('__LEGEND_BLOCK__', legendBlock);
html = html.replaceAll('__LEGEND_SRC__', legendSrc);
html = html.replaceAll('__STACKED_TRIM_BOTTOM__', String(Number.isFinite(stackedTrimBottom) ? stackedTrimBottom : -71));
html = html.replaceAll('__LEGEND_TRIM_TOP__', String(Number.isFinite(legendTrimTop) ? legendTrimTop : -58));
html = html.replaceAll('__LEGEND_TRIM_BOTTOM__', String(Number.isFinite(legendTrimBottom) ? legendTrimBottom : -58));
html = html.replaceAll('__COMBOS_TRIM_TOP__', String(Number.isFinite(combosTrimTop) ? combosTrimTop : -60));

(async () => {
  const browser = await chromium.launch({ args: [`--font-render-hinting=${hinting}`] });
  const context = await browser.newContext({
    deviceScaleFactor: Number.isFinite(scale) ? scale : 2,
  });
  const page = await context.newPage({ viewport: { width: 2000, height: 2000 } });

  await page.setContent(html, { waitUntil: 'load' });
  await page.waitForFunction(() => {
    const images = Array.from(document.querySelectorAll('img'));
    return images.every((img) => img.complete && img.naturalWidth > 0 && img.naturalHeight > 0);
  });

  const wrap = page.locator('#wrap');
  const box = await wrap.boundingBox();
  if (!box) {
    throw new Error('Failed to calculate composite bounding box.');
  }

  await page.setViewportSize({
    width: Math.ceil(box.width),
    height: Math.ceil(box.height),
  });
  await wrap.screenshot({ path: outputPngPath });
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
