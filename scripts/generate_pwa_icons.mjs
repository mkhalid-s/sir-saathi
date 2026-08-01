#!/usr/bin/env node

import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import sharp from 'sharp';

const root = resolve(import.meta.dirname, '..');
const sourcePath = resolve(root, 'apps/web/public/icons/icon.svg');
const checkOnly = process.argv.includes('--check');
const source = await readFile(sourcePath);
const variants = [
  { name: 'icon-192.png', size: 192 },
  { name: 'icon-512.png', size: 512 },
  { name: 'icon-maskable-512.png', size: 512 },
  { name: 'apple-touch-icon.png', size: 180 }
];

let mismatches = 0;
for (const variant of variants) {
  const outputPath = resolve(root, 'apps/web/public/icons', variant.name);
  const rendered = await sharp(source)
    .resize(variant.size, variant.size)
    .png({ adaptiveFiltering: false, compressionLevel: 9, palette: false })
    .toBuffer();
  if (checkOnly) {
    const current = await readFile(outputPath).catch(() => Buffer.alloc(0));
    if (!current.equals(rendered)) {
      console.error(`${variant.name} is missing or does not match icon.svg`);
      mismatches += 1;
    }
  } else {
    await writeFile(outputPath, rendered);
    console.log(`generated ${variant.name} (${variant.size}x${variant.size})`);
  }
}

if (mismatches) process.exitCode = 1;
