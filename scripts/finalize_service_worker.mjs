#!/usr/bin/env node

import { readdir, readFile, writeFile } from 'node:fs/promises';
import { extname, relative, resolve, sep } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const dist = resolve(root, 'apps/web/dist');
const serviceWorkerPath = resolve(dist, 'sw.js');
const marker = 'const BUILD_ASSET_URLS = [];';
const checkOnly = process.argv.includes('--check');
const eligibleExtensions = new Set(['.css', '.html', '.js', '.png', '.svg', '.webmanifest']);

async function filesUnder(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) files.push(...await filesUnder(path));
    else files.push(path);
  }
  return files;
}

function publicUrl(path) {
  const name = relative(dist, path).split(sep).join('/');
  if (name === 'index.html') return '/';
  if (name.endsWith('/index.html')) return `/${name.slice(0, -'index.html'.length)}`;
  return `/${name}`;
}

const buildAssets = (await filesUnder(dist))
  .filter((path) => path !== serviceWorkerPath && eligibleExtensions.has(extname(path)))
  .map(publicUrl)
  .sort();
const replacement = `const BUILD_ASSET_URLS = ${JSON.stringify(buildAssets, null, 2)};`;
const current = await readFile(serviceWorkerPath, 'utf8');

if (checkOnly) {
  if (current.includes(marker) || !current.includes(replacement)) {
    console.error('built service worker does not contain the complete generated asset list');
    process.exitCode = 1;
  } else {
    console.log(`verified ${buildAssets.length} offline build assets`);
  }
} else {
  if (!current.includes(marker)) throw new Error('service worker build-asset marker is missing');
  await writeFile(serviceWorkerPath, current.replace(marker, replacement));
  console.log(`precache includes ${buildAssets.length} generated assets`);
}
