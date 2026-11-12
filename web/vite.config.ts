import { rmSync } from 'node:fs'
import { resolve } from 'node:path'
import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig, type Plugin } from 'vite'
import { logosOff } from './src/lib/logoSwitch.ts'
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

// Logo takedown (WR-01): public/ is copied into dist/ unconditionally, so with VITE_LOGOS=off the
// flag alone would only hide logos in the UI while still serving /logos/*. Delete dist/logos after
// the build so a takedown deploy ships no logo files. Source logos stay in public/logos.
function dropLogos(): Plugin {
  let outDir = ''
  let off = false
  return {
    name: 'drop-logos',
    apply: 'build',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
      // config.env holds VITE_* from both .env files and process.env.
      off = logosOff(config.env.VITE_LOGOS)
    },
    closeBundle() {
      if (off) rmSync(resolve(outDir, 'logos'), { recursive: true, force: true })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [siteOrigin(), svelte(), dropLogos()],
})
