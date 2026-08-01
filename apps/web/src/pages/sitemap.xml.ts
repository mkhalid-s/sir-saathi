import type { APIRoute } from 'astro';
import { states } from '../data/states';
import { availableLocales, localizedPath } from '../lib/i18n';

export const prerender = true;

const basePaths = [
  '/',
  '/privacy/',
  '/methodology/',
  '/data-use/',
  '/languages/',
  ...states.map((state) => `/states/${state.stateId.toLowerCase()}/`)
];

export const GET: APIRoute = ({ site }) => {
  if (!site) throw new Error('Astro site URL is required to generate the sitemap');
  const locations = availableLocales.flatMap((locale) =>
    basePaths.map((path) => new URL(localizedPath(path, locale.code), site).href)
  );
  const body = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ...locations.map((location) => `  <url><loc>${location}</loc></url>`),
    '</urlset>',
    ''
  ].join('\n');
  return new Response(body, { headers: { 'Content-Type': 'application/xml; charset=utf-8' } });
};
