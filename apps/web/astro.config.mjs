import { defineConfig } from 'astro/config';
import preact from '@astrojs/preact';

const site = process.env.PUBLIC_SITE_URL ?? 'https://sir-saathi.example';
const siteUrl = new URL(site);
const releaseCommit = process.env.PUBLIC_RELEASE_COMMIT ?? 'development';
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
if (!siteUrl.hostname.endsWith('.example') && !/^[0-9a-f]{40}$/.test(releaseCommit)) {
  throw new Error('PUBLIC_RELEASE_COMMIT must be the full lowercase Git commit for a production build');
}

export default defineConfig({
  integrations: [preact()],
  output: 'static',
  site: siteUrl.toString(),
  markdown: {
    // This app has no syntax-highlighted content; disabling Shiki prevents it
    // from introducing inline style attributes outside the hash-only policy.
    syntaxHighlight: false
  },
  security: {
    csp: {
      algorithm: 'SHA-256',
      directives: [
        "default-src 'none'",
        "base-uri 'none'",
        "object-src 'none'",
        "form-action 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self' https://challenges.cloudflare.com",
        "frame-src https://challenges.cloudflare.com",
        "worker-src 'self'",
        "manifest-src 'self'"
      ],
      scriptDirective: {
        resources: ["'self'", 'https://challenges.cloudflare.com']
      },
      styleDirective: {
        resources: ["'self'"]
      }
    }
  }
});
