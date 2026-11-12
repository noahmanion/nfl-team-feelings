import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig, type Plugin } from 'vite'
import { resolveSiteOrigin } from './src/lib/siteOrigin.ts'

// Replaces %SITE_ORIGIN% in index.html with the absolute production origin.
// order 'pre' so Vite's asset scan sees absolute URLs, not root-relative ones.
function siteOrigin(): Plugin {
  const origin = resolveSiteOrigin(process.env)
  return {
    name: 'site-origin',
    transformIndexHtml: {
      order: 'pre',
      handler: (html) => html.replaceAll('%SITE_ORIGIN%', origin),
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [siteOrigin(), svelte()],
})
