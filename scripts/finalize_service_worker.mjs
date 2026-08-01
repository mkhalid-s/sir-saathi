#!/usr/bin/env node

import { readdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { extname, relative, resolve, sep } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const dist = resolve(root, 'apps/web/dist');
const serviceWorkerPath = resolve(dist, 'sw.js');
const releaseManifestPath = resolve(dist, 'release-manifest.json');
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

function sha256(value) {
  return createHash('sha256').update(value).digest('hex');
}

const htmlFiles = (await filesUnder(dist))
  .filter((path) => extname(path) === '.html' && !path.endsWith(`${sep}404.html`))
  .sort();
const indexHtml = await readFile(resolve(dist, 'index.html'), 'utf8');
const releaseMatch = indexHtml.match(/<meta name="sir-saathi-release" content="([0-9a-f]{40}|development)">/);
if (!releaseMatch) throw new Error('built homepage is missing the governed release identity');
const releaseManifest = {
  schema_version: 1,
  release_commit: releaseMatch[1],
  route_count: htmlFiles.length,
  routes: await Promise.all(htmlFiles.map(async (path) => ({
    path: publicUrl(path),
    sha256: sha256(await readFile(path))
  })))
};
const releaseManifestJson = `${JSON.stringify(releaseManifest, null, 2)}\n`;

if (checkOnly) {
  const currentManifest = await readFile(releaseManifestPath, 'utf8');
  if (currentManifest !== releaseManifestJson) {
    console.error('release manifest does not match the complete generated HTML route set');
    process.exitCode = 1;
  }
} else {
  await writeFile(releaseManifestPath, releaseManifestJson);
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
    console.log(`verified ${buildAssets.length} offline build assets and ${htmlFiles.length} release routes`);
  }
} else {
  if (!current.includes(marker)) throw new Error('service worker build-asset marker is missing');
  await writeFile(serviceWorkerPath, current.replace(marker, replacement));
  console.log(`precache includes ${buildAssets.length} generated assets; release manifest covers ${htmlFiles.length} routes`);
}
