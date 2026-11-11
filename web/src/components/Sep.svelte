<!--
  The one dot separator for header/meta lines (WR-01). Svelte trims whitespace between tags, so the
  spacing must not come from source whitespace or from a per-call-site class: it lives here, in the
  separator's own scoped style, and is applied wherever <Sep /> renders (including inside {#if}).
  Don't hand-roll `<span class="sep">` elsewhere; sep.test.ts guards against that.
-->
<span class="sep" aria-hidden="true">·</span>

<style>
  .sep {
    display: inline-block;
    margin-inline: var(--space-xs);
    color: var(--text-muted);
  }
</style>
