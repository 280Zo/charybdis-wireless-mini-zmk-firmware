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
 * - Applies workflow-controlled styling/layout (solid background, spacing, trims, alpha)
 * - Captures a PNG (default: keymap-drawer/stacked/stacked-combos.png)
 *
 * How it is used:
 * - Called by `.github/workflows/draw_keymaps.yml` in the step:
 *   "Render composite PNG with Playwright"
 * - Typical invocation:
 *   node scripts/render_stacked_composite.js
 *
 * Main env knobs (set in draw_keymaps.yml):
 * - KEYMAP_BG                   : composite background color
 * - KEYMAP_OUTPUT               : output PNG path (used for dark/light variants)
 * - KEYMAP_STYLE_THEME          : key/legend palette theme ("dark" or "light"), defaults to dark
 * - KEYMAP_CORNER_LEGEND_WRAP_OVERRIDES: JSON list of corner-wrap overrides
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
const outputPngPath = process.env.KEYMAP_OUTPUT || 'keymap-drawer/stacked/stacked-combos.png';

const bg = process.env.KEYMAP_BG || '#282828';
const alphaCapture = ['1', 'true', 'yes', 'on'].includes((process.env.KEYMAP_ALPHA || '0').toLowerCase());
const gap = Number.parseInt(process.env.KEYMAP_GAP || '0', 10);
const margin = Number.parseInt(process.env.KEYMAP_MARGIN || '10', 10);
const scale = Number.parseFloat(process.env.KEYMAP_SCALE || '2');
const hinting = process.env.KEYMAP_HINTING || 'medium';
const legendOn = (process.env.KEYMAP_LEGEND || '1') !== '0';
const styleTheme = (process.env.KEYMAP_STYLE_THEME || 'dark').toLowerCase();
const stackedTrimBottom = Number.parseInt(process.env.KEYMAP_STACKED_TRIM_BOTTOM || '-71', 10);
const legendTrimTop = Number.parseInt(process.env.KEYMAP_LEGEND_TRIM_TOP || '-58', 10);
const legendTrimBottom = Number.parseInt(process.env.KEYMAP_LEGEND_TRIM_BOTTOM || '-58', 10);
const combosTrimTop = Number.parseInt(process.env.KEYMAP_COMBOS_TRIM_TOP || '-60', 10);
const cornerLegendWrapOverridesRaw = process.env.KEYMAP_CORNER_LEGEND_WRAP_OVERRIDES || '[]';

const readText = (path) => fs.readFileSync(path, 'utf8');
const toDataUrl = (svg) => `data:image/svg+xml;base64,${Buffer.from(svg, 'utf8').toString('base64')}`;

const applyThemeAliases = (svg, theme) => {
  const normalized = theme === 'light' ? 'light' : 'dark';
  // Rewrite active alias bindings like:
  // --stack-key-fill: var(--stack-key-fill-dark);
  // to:
  // --stack-key-fill: var(--stack-key-fill-light);
  return svg.replace(
    /(--[a-z0-9-]+)\s*:\s*var\(\s*(--[a-z0-9-]+)-(dark|light)\s*\)\s*;/gi,
    (full, alias, base) => (alias === base ? `${alias}: var(${base}-${normalized});` : full),
  );
};

const parseCornerLegendWrapOverrides = (raw) => {
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    throw new Error(`Invalid KEYMAP_CORNER_LEGEND_WRAP_OVERRIDES JSON: ${err.message}`);
  }
  if (!Array.isArray(parsed)) {
    throw new Error('KEYMAP_CORNER_LEGEND_WRAP_OVERRIDES must decode to a JSON array');
  }
  return parsed;
};

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const escapeXml = (value) => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&apos;');
const normalizeText = (value) => value.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();

const buildMultilineTspans = ({ x, lines, tspanStyle = '', lineHeightEm = 1.05 }) => {
  const styleAttr = tspanStyle ? ` style="${escapeXml(tspanStyle)}"` : '';
  const firstDy = -(((lines.length - 1) * lineHeightEm) / 2);
  return lines.map((line, idx) => {
    const dy = `${(idx === 0 ? firstDy : lineHeightEm).toFixed(2)}em`;
    return `<tspan x="${escapeXml(String(x))}" dy="${dy}"${styleAttr}>${escapeXml(String(line))}</tspan>`;
  }).join('');
};

const applyCornerLegendWrap = (svg, override) => {
  const keypos = Number.parseInt(override.keypos, 10);
  const corner = String(override.corner || '');
  const lines = Array.isArray(override.lines) ? override.lines : [];
  if (!Number.isFinite(keypos) || !corner || lines.length < 2) return svg;

  const groupRegex = new RegExp(`(<g[^>]*class="[^"]*\\bkeypos-${keypos}\\b[^"]*"[^>]*>[\\s\\S]*?<\\/g>)`);
  const groupMatch = svg.match(groupRegex);
  if (!groupMatch) return svg;

  let replaced = false;
  const cornerClass = escapeRegExp(corner);
  const textRegex = new RegExp(`<text([^>]*)class="([^"]*\\b${cornerClass}\\b[^"]*)"([^>]*)>([\\s\\S]*?)<\\/text>`, 'g');

  const wrappedGroup = groupMatch[1].replace(textRegex, (full, pre, cls, post, inner) => {
    if (replaced) return full;
    if (override.from && normalizeText(inner) !== String(override.from)) return full;

    const attrs = `${pre}${post}`;
    const xMatch = attrs.match(/\bx="([^"]+)"/);
    const yMatch = attrs.match(/\by="([^"]+)"/);

    const xBase = Number.parseFloat(xMatch ? xMatch[1] : '0');
    const yBase = Number.parseFloat(yMatch ? yMatch[1] : '0');
    const xOffset = Number.parseFloat(String(override.x_offset ?? '0'));
    const yOffset = Number.parseFloat(String(override.y_offset ?? '0'));
    const x = Number.isFinite(xBase) && Number.isFinite(xOffset) ? xBase + xOffset : (xMatch ? xMatch[1] : '0');
    const y = Number.isFinite(yBase) && Number.isFinite(yOffset) ? yBase + yOffset : (yMatch ? yMatch[1] : '0');
    const textStyle = String(override.text_style || '').trim();

    const tspans = buildMultilineTspans({
      x,
      lines,
      tspanStyle: String(override.tspan_style || ''),
      lineHeightEm: Number.isFinite(Number(override.line_height_em)) ? Number(override.line_height_em) : 1.05,
    });
    replaced = true;
    return `<text x="${escapeXml(String(x))}" y="${escapeXml(String(y))}" class="${cls}"${
      textStyle ? ` style="${escapeXml(textStyle)}"` : ''
    }>${tspans}</text>`;
  });

  if (!replaced) return svg;
  return svg.replace(groupMatch[1], wrappedGroup);
};

const applyCornerLegendWrapOverrides = (svg, overrides) => {
  let out = svg;
  for (const override of overrides) {
    out = applyCornerLegendWrap(out, override);
  }
  return out;
};

const cornerLegendWrapOverrides = parseCornerLegendWrapOverrides(cornerLegendWrapOverridesRaw);
let stackedSvg = readText(stackedSvgPath);
stackedSvg = applyThemeAliases(stackedSvg, styleTheme);
stackedSvg = applyCornerLegendWrapOverrides(stackedSvg, cornerLegendWrapOverrides);
const stackedSrc = toDataUrl(stackedSvg);
let combosSvg = readText(combosSvgPath);
combosSvg = applyThemeAliases(combosSvg, styleTheme);
const combosSrc = toDataUrl(combosSvg);
let legendSrc = '';
if (legendOn) {
  let legendSvg = readText(legendSvgPath);
  legendSvg = applyThemeAliases(legendSvg, styleTheme);
  legendSrc = toDataUrl(legendSvg);
}

const legendBlock = legendOn
  ? '<div class="block"><img id="legend-svg" src="__LEGEND_SRC__" alt="legend key" /></div>'
  : '';

let html = fs.readFileSync(templatePath, 'utf8');
html = html.replaceAll('__KEYMAP_BG__', bg);
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
