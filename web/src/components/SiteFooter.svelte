<script lang="ts">
  import { formatDate, formatDateOnly } from '../lib/format'
  import type { Meta } from '../lib/types'

  let { meta }: { meta?: Meta } = $props()
</script>

<footer class="site-footer">
  {#if meta}
    <p class="stamp">
      <span class="part">Last updated {formatDate(meta.generated_at)}</span>
      <span class="part second">Data through {formatDateOnly(meta.data_through)}</span>
    </p>
  {/if}
  <p class="disclaimer" class:solo={!meta}>
    Unofficial fan project — not affiliated with the NFL. Data: <a href="https://github.com/nflverse">nflverse</a>.
  </p>
</footer>

<style>
  .site-footer {
    margin-top: var(--space-xl);
    font-size: var(--text-label);
    line-height: var(--lh-label);
    color: var(--text-muted);
  }
  .stamp {
    margin-bottom: 0;
  }
  .disclaimer {
    margin-top: var(--space-xs);
  }
  .disclaimer.solo {
    margin-top: revert;
  }
  .part {
    display: block;
  }
  @media (min-width: 1024px) {
    .part {
      display: inline;
    }
    .second::before {
      content: ' · ';
    }
  }
</style>
