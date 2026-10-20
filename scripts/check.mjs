#!/usr/bin/env node
// Static build gate for AstralSurge OS. No dependencies; runs on Node 20+.
// Fails with a non-zero exit code if any check fails.
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = (file) => readFileSync(join(root, file), 'utf8');
const failures = [];
const check = (name, ok, detail = '') => {
  console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${detail ? ` - ${detail}` : ''}`);
  if (!ok) failures.push(name);
};

// 1. Application HTML: exactly one inline script block that must parse.
const html = read('index.html');
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]);
check('index.html has an inline app script', scripts.length >= 1, `${scripts.length} block(s)`);
scripts.forEach((code, i) => {
  try {
    new vm.Script(code, { filename: `index.html#script${i}` }); // compile only, never execute
    check(`inline script ${i} parses`, true);
  } catch (error) {
    check(`inline script ${i} parses`, false, error.message);
  }
});

// 2. No dynamic code evaluation anywhere in the shipped app.
const appSource = [html, read('sw.js')].join('\n');
check('no eval()', !/\beval\s*\(/.test(appSource));
check('no new Function()', !/new\s+Function\s*\(/.test(appSource));

// 3. Content-Security-Policy present and not weakened by unsafe-eval.
const csp = html.match(/http-equiv="Content-Security-Policy"\s+content="([^"]+)"/i);
check('index.html declares a Content-Security-Policy', Boolean(csp));
check('CSP does not allow unsafe-eval', !(csp && /unsafe-eval/.test(csp[1])));
check('CSP restricts connections (connect-src none or self)', Boolean(csp) && /connect-src\s+('none'|'self')/.test(csp[1]));

// 4. No third-party network dependencies in markup or CSS.
const externalRef = /\b(src|href)\s*=\s*["']?\s*https?:|url\(\s*['"]?https?:|@import\s+(url\()?\s*['"]?https?:/i;
check('no external src/href/url() references in index.html', !externalRef.test(html));

// 5. Service worker: valid syntax, app-shell files exist, cache name is versioned.
const sw = read('sw.js');
try {
  new vm.Script(sw, { filename: 'sw.js' });
  check('sw.js parses', true);
} catch (error) {
  check('sw.js parses', false, error.message);
}
const cacheName = sw.match(/const CACHE_NAME = '([^']+)'/);
check('sw.js has a versioned CACHE_NAME', Boolean(cacheName) && /^astralsurge-os-v[\d.]+$/.test(cacheName[1]), cacheName?.[1] ?? 'missing');
const shell = [...sw.matchAll(/new URL\('\.\/([^']*)'/g)].map((m) => m[1].split('?')[0]).map((p) => p || 'index.html');
for (const file of new Set(shell)) {
  check(`app-shell file exists: ${file}`, existsSync(join(root, file)));
}
const externalCache = /new URL\('https?:/.test(sw);
check('service worker caches no external origins', !externalCache);

// 6. Manifest parses and points at local start URL.
try {
  const manifest = JSON.parse(read('manifest.json'));
  check('manifest.json parses', true);
  check('manifest start_url is relative', typeof manifest.start_url === 'string' && manifest.start_url.startsWith('./'));
} catch (error) {
  check('manifest.json parses', false, error.message);
}

// 7. GitHub Pages deployment files.
check('CNAME present', existsSync(join(root, 'CNAME')));
check('.nojekyll present', existsSync(join(root, '.nojekyll')));

// 8. Bundled fonts: local files only, precached for offline use, licensed under SIL OFL,
//    and every font setting has a matching CSS rule.
const fontUrls = [...html.matchAll(/url\(\s*["']?(fonts\/[^"')\s]+)["']?\s*\)/g)].map((m) => m[1]);
check('index.html declares bundled font faces', fontUrls.length >= 1, `${fontUrls.length} font file(s)`);
for (const file of new Set(fontUrls)) {
  check(`bundled font exists: ${file}`, existsSync(join(root, file)));
  check(`bundled font is precached: ${file}`, sw.includes(`'./${file}'`));
}
const fontFiles = readdirSync(join(root, 'fonts')).filter((f) => /\.woff2?$/.test(f));
check('every font file under fonts/ is referenced by a font face', fontFiles.every((f) => fontUrls.includes(`fonts/${f}`)));
const licenses = existsSync(join(root, 'fonts/licenses')) ? readdirSync(join(root, 'fonts/licenses')) : [];
const oflFiles = licenses.filter((f) => /^OFL-.+\.txt$/.test(f));
check('each bundled font family ships an OFL license', oflFiles.length >= 5, `${oflFiles.length} license file(s)`);
for (const file of oflFiles) {
  check(`license text is SIL OFL: ${file}`, /SIL OPEN FONT LICENSE|SIL Open Font License/i.test(read(`fonts/licenses/${file}`)));
}
const fontOptions = [...html.matchAll(/\['([a-z]+)','[^']*'\]/g)].map((m) => m[1]);
const fontOptionsBlock = html.match(/const FONT_OPTIONS=\[([\s\S]*?)\];/);
const optionKeys = fontOptionsBlock ? [...fontOptionsBlock[1].matchAll(/\['([a-z]+)'/g)].map((m) => m[1]) : [];
check('FONT_OPTIONS is declared', optionKeys.length >= 5, `${optionKeys.length} option(s)`);
for (const key of optionKeys) {
  check(`font option has a CSS rule: ${key}`, html.includes(`html[data-font="${key}"] body{`));
}
const deploy = read('.github/workflows/pages.yml');
check('Pages deploy copies fonts/', /cp -r fonts _site\//.test(deploy));

if (failures.length) {
  console.error(`\n${failures.length} check(s) failed.`);
  process.exit(1);
}
console.log('\nAll static checks passed.');
