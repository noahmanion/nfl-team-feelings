<script lang="ts">
  import MethodologyChart from './MethodologyChart.svelte'
  import Sep from './Sep.svelte'
  import StatusPanel from './StatusPanel.svelte'
  import { loadMethodology } from '../lib/data'
  import { formatDateOnly, moodToken } from '../lib/format'
  import {
    chartCandidates,
    chartRows,
    ciMethodText,
    intervalCaption,
    deltaText,
    effectText,
    foldText,
    formatCI,
    formatDelta,
    formatDeltaCI,
    formatMetric,
    formatWeight,
    verdictLead,
  } from '../lib/methodology'
  import type { Meta, Methodology, PeriodMetrics } from '../lib/types'

  let { meta }: { meta: Meta } = $props()

  let m = $state<Methodology | null>(null)
  let failed = $state(false)
  let retry = $state(0)

  $effect(() => {
    void retry
    failed = false
    let live = true
    loadMethodology(meta).then(
      (d) => {
        if (live) m = d
      },
      (err) => {
        console.error(err)
        if (live) failed = true
      },
    )
    return () => {
      live = false
    }
  })

  const span = (s: [number, number]) => `${s[0]}–${String(s[1]).slice(-2)}`

  const periods = $derived.by(() => {
    if (!m) return []
    type P = { label: string; spearman: PeriodMetrics; brier: PeriodMetrics; spMethod: string | null; brMethod: string | null }
    const out: P[] = []
    for (const b of [m.walk_forward, m.holdout]) {
      if (!b) continue
      out.push({
        label: b.label, spearman: b.spearman_n8, brier: b.brier,
        spMethod: ciMethodText(b, 'spearman_n8'), brMethod: ciMethodText(b, 'brier'),
      })
    }
    return out
  })
  const wfDiff = $derived(m?.walk_forward?.diff?.spearman_n8 ?? null)
  const hoDiff = $derived(m?.holdout?.diff?.spearman_n8 ?? null)
  const hoN4 = $derived(m?.holdout?.diff?.spearman_n4 ?? null)
  const hoBrier = $derived(m?.holdout?.diff?.brier_vs_elo ?? null)
  const excludesZero = (ci?: [number, number] | null) => !!ci && (ci[0] > 0 || ci[1] < 0)
</script>

<article class="methodology">
  {#if failed}
    <StatusPanel
      variant="error"
      title="Couldn’t load the methodology"
      body="The methodology data didn’t load."
      actions={[{ label: 'Try again', onClick: () => retry++ }]}
    />
  {:else if !m}
    <p class="muted" role="status">Loading…</p>
  {:else}
    <section>
      <h2>What the score is</h2>
      <p>
        The feel-good score adds up {m.factors.length} factors. Each one is turned into a z-score across the teams in
        the same week, multiplied by its weight, and summed.
      </p>
      <p>
        The number you see (0–100) is that sum’s percentile against every preseason and regular-season team-week from
        {span(m.split.reference)}. A score of 50 is an ordinary week; 90 means it beat 90% of them.
      </p>
      {#if m.frozen}
        <p>
          The weights were fit on {span(m.frozen.fit_seasons)} and frozen on {formatDateOnly(m.frozen.fitted_at)}. They
          are never refit during the season.
        </p>
      {/if}
      <p>
        <span class="strong">What it tries to predict:</span>
        {m.target.text}
      </p>
      <ul class="bands" aria-label="Mood bands">
        {#each meta.bands as b, i (b.min)}
          <li>
            <span class="chip" style:background={`var(--mood-${moodToken(i, meta.bands.length)})`}></span>
            <span aria-hidden="true">{b.emoji}</span>
            <span>{b.label}</span>
            <span class="muted">{b.min}–{b.max}</span>
          </li>
        {/each}
      </ul>
    </section>

    <section>
      <h2>The factors</h2>
      <p class="muted">
        Weights are points of next-8-games margin per standard deviation of the factor. Negative and near-zero weights
        are shown as fitted. “Same sign” counts the walk-forward seasons whose refit agreed with the final sign; “Added”
        is the change in rank correlation when the factor joins the ones above it.
      </p>
      <ol class="rows">
        {#each m.factors as f (f.key)}
          <li class="row">
            <p class="strong">{f.label}</p>
            <p class="muted">{f.description}</p>
            <p class="meta">
              <span>Weight <span class="num">{formatWeight(f.weight)}</span></span><Sep /><span>{effectText(f.effect)}</span><Sep
              /><span>{foldText(f.fold_sign)}</span>{#if f.delta_spearman_n8 != null || f.baseline_spearman_n8 != null}<Sep
                /><span>Added <span class="num">{deltaText(f.delta_spearman_n8, f.baseline_spearman_n8)}</span></span>{/if}
            </p>
          </li>
        {/each}
      </ol>
    </section>

    <section>
      <h2>Does it work?</h2>
      <p class="strong">{verdictLead(m)}</p>
      {#if wfDiff?.seasons_won != null && wfDiff.of != null}
        <p>
          In the walk-forward test the feel-good score ranked teams better than Elo alone in {wfDiff.seasons_won} of
          {wfDiff.of} seasons.
        </p>
      {/if}
      {#if m.holdout && hoDiff}
        <p>
          On the holdout it won {hoDiff.seasons_won} of {hoDiff.of} seasons against Elo alone. Difference in rank
          correlation: <span class="num">{formatDelta(hoDiff.value, 3)}</span>, 95% interval
          <span class="num">{formatDeltaCI(hoDiff.ci_season)}</span> by season blocks and
          <span class="num">{formatDeltaCI(hoDiff.ci_cluster)}</span> by team-season.
        </p>
      {/if}
      {#if m.holdout && (hoN4?.value != null || hoBrier?.value != null)}
        <p>
          {#if hoN4?.value != null}
            Over the next 4 games instead of 8 the difference was <span class="num">{formatDelta(hoN4.value)}</span>
            (<span class="num">{formatDeltaCI(hoN4.ci_season)}</span> by season blocks,
            <span class="num">{formatDeltaCI(hoN4.ci_cluster)}</span> by team-season).
          {/if}
          {#if hoBrier?.value != null}
            On single games the score was {hoBrier.value > 0 ? 'worse than' : hoBrier.value < 0 ? 'better than' : 'level with'}
            Elo alone: next-game Brier difference <span class="num">{formatDelta(hoBrier.value, 4)}</span> (lower is
            better), interval <span class="num">{formatDeltaCI(hoBrier.ci_season, 4)}</span> by season blocks{#if excludesZero(hoBrier.ci_season)}
              (excludes zero){/if} and <span class="num">{formatDeltaCI(hoBrier.ci_cluster, 4)}</span> by
            season-week{#if excludesZero(hoBrier.ci_cluster)} (excludes zero){/if}.
          {/if}
        </p>
      {/if}
      <p class="muted">
        “Rank correlation” (Spearman) measures how well each week’s ranking matches how teams actually did over their next
        8 games. The walk-forward test ({m.walk_forward ? span(m.walk_forward.seasons) : span(m.split.walk_forward)})
        refits the weights each season using only earlier seasons. The holdout ({span(m.split.holdout)}) uses the frozen
        weights, once. The Brier score checks single-game win chances, where the Vegas spread is the ceiling.
      </p>

      {#if periods.length > 0}
        <MethodologyChart
          rows={chartRows(m, 'spearman_n8')}
          metric="spearman_n8"
          label="Rank correlation by method"
          intervalNote={intervalCaption(m, 'spearman_n8')}
        />
        <MethodologyChart
          rows={chartRows(m, 'brier')}
          metric="brier"
          label="Brier score by method"
          intervalNote={intervalCaption(m, 'brier')}
        />

        <h3>The numbers</h3>
        <ol class="rows">
          {#each chartCandidates(m, 'brier') as c (c.key)}
            <li class="row">
              <p class="strong">{c.label}</p>
              {#each periods as p (p.label)}
                <p class="meta">
                  <span class="muted">{p.label}</span><Sep />{#if !c.brier_only}<span
                      >Rank corr. <span class="num">{formatMetric(p.spearman[c.key]?.value)}</span>
                      <span class="muted num">({formatCI(p.spearman[c.key]?.ci)}{p.spMethod ? `, ${p.spMethod}` : ''})</span></span
                    ><Sep />{/if}<span>Brier <span class="num">{formatMetric(p.brier[c.key]?.value)}</span>
                    <span class="muted num">({formatCI(p.brier[c.key]?.ci)}{p.brMethod ? `, ${p.brMethod}` : ''})</span></span>
                </p>
              {/each}
            </li>
          {/each}
        </ol>
      {:else}
        <p class="muted">No backtest evidence has been exported yet.</p>
      {/if}
    </section>

    <section>
      <h2>Honest notes</h2>
      <ul class="notes">
        {#each m.notes as n (n.key)}
          <li>{n.text}</li>
        {/each}
      </ul>
    </section>
  {/if}
</article>

<style>
  .methodology {
    max-width: 680px;
    display: flex;
    flex-direction: column;
    gap: var(--space-xl);
    font-size: var(--text-body);
    line-height: var(--lh-body);
  }
  section {
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
    min-width: 0;
  }
  h2 {
    font-size: var(--text-heading);
    line-height: var(--lh-heading);
    font-weight: var(--weight-semibold);
  }
  h3 {
    font-size: var(--text-body);
    font-weight: var(--weight-semibold);
  }
  .strong {
    font-weight: var(--weight-semibold);
  }
  .muted {
    color: var(--text-muted);
  }
  .num {
    font-variant-numeric: tabular-nums;
  }
  .bands {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .bands li {
    display: flex;
    align-items: center;
    gap: var(--space-sm);
  }
  .chip {
    inline-size: var(--chip-size);
    block-size: var(--chip-size);
    border-radius: var(--radius-sm);
    flex: none;
  }
  .rows {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .row {
    background: var(--surface);
    border-radius: var(--radius-md);
    padding: var(--space-md);
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
    min-width: 0;
  }
  .meta {
    font-size: var(--text-label);
    line-height: var(--lh-label);
    overflow-wrap: anywhere;
  }
  .notes {
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
    margin: 0;
    padding-inline-start: var(--space-lg);
  }
</style>
