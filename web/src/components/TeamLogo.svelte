<script lang="ts">
  import { logoSrc, logosEnabled } from '../lib/logos'
  import TeamChip from './TeamChip.svelte'

  // Team logo with chip fallback (D-11, D-13, D-14). Falls back to the color chip for unknown
  // franchises, when VITE_LOGOS=off, or after the image fails to load.
  let {
    franchise,
    primary = null,
    secondary = null,
    size = 24,
    alt = '',
  }: {
    franchise: string
    primary?: string | null
    secondary?: string | null
    size?: 16 | 20 | 24 | 32 | 48
    alt?: string
  } = $props()

  const src = $derived(logosEnabled() ? logoSrc(franchise) : null)
  // Keyed to the failing src, so a failure never sticks after navigating to another team.
  let failedSrc = $state<string | null>(null)
  const showImg = $derived(src !== null && failedSrc !== src)
</script>

{#if showImg}
  <span class="logo" style:--logo-size="{size}px">
    <img
      {src}
      width={size}
      height={size}
      {alt}
      loading="lazy"
      decoding="async"
      aria-hidden={alt === '' ? 'true' : undefined}
      onerror={() => (failedSrc = src)}
    />
  </span>
{:else}
  <TeamChip {primary} {secondary} {size} />
{/if}

<style>
  .logo {
    display: inline-grid;
    place-items: center;
    flex: none;
    width: var(--logo-size);
    height: var(--logo-size);
  }
  .logo img {
    width: 100%;
    height: 100%;
    object-fit: contain;
  }
  /* Dark mode: logos sit on a light disc so dark marks stay legible; no filter or recolor. */
  @media (prefers-color-scheme: dark) {
    .logo {
      background: var(--logo-disc);
      border-radius: 50%;
    }
    .logo img {
      width: 76%;
      height: 76%;
    }
  }
</style>
