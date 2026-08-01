import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

const site = process.env.PUBLIC_SITE_URL ?? 'https://sir-saathi.example';
const siteUrl = new URL(site);
if (
  siteUrl.protocol !== 'https:'
  || siteUrl.username
  || siteUrl.password
  || siteUrl.pathname !== '/'
  || siteUrl.search
  || siteUrl.hash
) {
  throw new Error('PUBLIC_SITE_URL must be an HTTPS origin without credentials, path, query, or fragment');
}

export default defineConfig({
  integrations: [preact()],
  output: 'static',
  site: siteUrl.toString()
});
