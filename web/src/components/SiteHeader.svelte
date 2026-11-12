<script lang="ts">
  import Sep from './Sep.svelte'
  import { historyHash, methodologyHash, recordsHash } from '../lib/router'

  // 'team': neither nav link is the current page.
  let { current = 'board' }: { current?: 'board' | 'history' | 'team' | 'records' | 'methodology' } = $props()
</script>

<header class="site-header">
  <p class="wordmark">Feel-Good Score</p>
  <h1>How should you feel about your team?</h1>
  <p class="subhead">Every NFL team, ranked by how good their fans should feel right now.</p>
  <!-- WR-10: each separator travels with the link after it, so a wrapped line (320-375px) starts
       with "· How it works" instead of leaving a dangling "·" at the end of the line above. -->
  <nav aria-label="Views">
    <a href="#/" aria-current={current === 'board' ? 'page' : undefined}>Board</a>
    <span class="item"
      ><Sep /><a href={historyHash()} aria-current={current === 'history' ? 'page' : undefined}>Mood over time</a></span
    >
    <span class="item"
      ><Sep /><a href={recordsHash} aria-current={current === 'records' ? 'page' : undefined}>Records</a></span
    >
    <span class="item"
      ><Sep /><a href={methodologyHash} aria-current={current === 'methodology' ? 'page' : undefined}>How it works</a
      ></span
    >
  </nav>
</header>

<style>
  .site-header {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
  }
  .wordmark {
    font-weight: var(--weight-semibold);
  }
  h1 {
    margin-top: var(--space-md);
    font-size: var(--text-display);
    line-height: var(--lh-display);
    font-weight: var(--weight-semibold);
  }
  .subhead {
    color: var(--text-muted);
  }
  nav {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    /* the Sep's own margin-inline is the only horizontal spacing */
    gap: 0;
    margin-top: var(--space-sm);
  }
  .item {
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
  }
  nav a {
    display: inline-flex;
    align-items: center;
    min-block-size: var(--tap-min);
    color: var(--text);
    font-size: var(--text-body);
    text-decoration: none;
    border-bottom: 2px solid transparent;
  }
  nav a[aria-current='page'] {
    border-bottom-color: var(--accent);
  }
  nav a:hover {
    border-bottom-color: var(--border);
  }
  nav a[aria-current='page']:hover {
    border-bottom-color: var(--accent);
  }
  nav a:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
  @media (min-width: 1024px) {
    h1 {
      margin-top: var(--space-2xl);
    }
  }
</style>
