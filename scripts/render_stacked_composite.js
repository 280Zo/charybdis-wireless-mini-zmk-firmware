const fs = require('fs');
const { chromium } = require('playwright');

/**
 * Composite keymap renderer (Playwright).
 *
 * What this script does:
 * - Loads three SVG artifacts produced earlier in the workflow:
 *   1) stacked.svg
 *   2) legend.svg (optional)
 *   3) combos.svg
 * - Injects them into keymap-drawer/stacked/composite-template.html
 * - Applies workflow-controlled styling/layout (gradient background, spacing, trims, alpha)
 * - Captures a single PNG: keymap-drawer/stacked/stacked-combos.png
 *
 * How it is used:
 * - Called by `.github/workflows/draw_keymaps.yml` in the step:
 *   "Render composite PNG with Playwright"
 * - Typical invocation:
 *   node scripts/render_stacked_composite.js
 *
 * Main env knobs (set in draw_keymaps.yml):
 * - KEYMAP_BG / KEYMAP_BG_END   : composite gradient colors
 * - KEYMAP_ALPHA                : when truthy, PNG keeps alpha (omitBackground)
 * - KEYMAP_GAP / KEYMAP_MARGIN  : vertical spacing and outer padding
 * - KEYMAP_SCALE / KEYMAP_HINTING: screenshot scale and Chromium font hinting
 * - KEYMAP_LEGEND               : include/exclude legend block
 * - KEYMAP_*_TRIM_*             : overlap trims between stacked/legend/combos blocks
 *
 * Where to modify behavior:
 * - Layout/CSS structure: keymap-drawer/stacked/composite-template.html
 * - Pipeline env defaults: .github/workflows/draw_keymaps.yml
 * - Screenshot logic (clip/alpha/viewport): this file, near page.screenshot(...)
 */
const templatePath = 'keymap-drawer/stacked/composite-template.html';
const stackedSvgPath = 'keymap-drawer/stacked/stacked.svg';
const combosSvgPath = 'keymap-drawer/stacked/combos.svg';
const legendSvgPath = 'keymap-drawer/stacked/legend.svg';
const outputPngPath = 'keymap-drawer/stacked/stacked-combos.png';

const bg = process.env.KEYMAP_BG || '#2F4858';
const bgEnd = process.env.KEYMAP_BG_END || '#272727';
const alphaCapture = ['1', 'true', 'yes', 'on'].includes((process.env.KEYMAP_ALPHA || '0').toLowerCase());
const gap = Number.parseInt(process.env.KEYMAP_GAP || '0', 10);
const margin = Number.parseInt(process.env.KEYMAP_MARGIN || '10', 10);
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
html = html.replaceAll('__KEYMAP_BG_END__', bgEnd);
html = html.replaceAll('__KEYMAP_GAP__', String(Number.isFinite(gap) ? gap : 0));
html = html.replaceAll('__KEYMAP_MARGIN__', String(Number.isFinite(margin) ? margin : 10));
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

  // Measure only the composite wrapper and clip screenshot to that region.
  const wrap = page.locator('#wrap');
  const box = await wrap.boundingBox();
  if (!box) {
    throw new Error('Failed to calculate composite bounding box.');
  }

  // Expand viewport to fully contain the clip region, then capture page clip.
  // `omitBackground` preserves transparency when KEYMAP_ALPHA is enabled.
  await page.setViewportSize({
    width: Math.ceil(box.x + box.width),
    height: Math.ceil(box.y + box.height),
  });
  await page.screenshot({
    path: outputPngPath,
    clip: {
      x: Math.floor(box.x),
      y: Math.floor(box.y),
      width: Math.ceil(box.width),
      height: Math.ceil(box.height),
    },
    omitBackground: alphaCapture,
  });
  await browser.close();
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
