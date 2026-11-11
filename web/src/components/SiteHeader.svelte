<script lang="ts">
  import Sep from './Sep.svelte'

  // 'team': neither nav link is the current page.
  let { current = 'board' }: { current?: 'board' | 'history' | 'team' } = $props()
</script>

<header class="site-header">
  <p class="wordmark">Feel-Good Score</p>
  <h1>How should you feel about your team?</h1>
  <p class="subhead">Every NFL team, ranked by how good their fans should feel right now.</p>
  <nav aria-label="Views">
    <a href="#/" aria-current={current === 'board' ? 'page' : undefined}>Board</a>
    <Sep />
    <a href="#/history" aria-current={current === 'history' ? 'page' : undefined}>Mood over time</a>
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
    align-items: center;
    gap: var(--space-xs);
    margin-top: var(--space-sm);
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
