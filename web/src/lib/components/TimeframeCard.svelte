<script lang="ts">
	import type { TimeframeAnalysisOut } from '$lib/api/types';
	import { formatPrice } from '$lib/format';

	let { analysis, title }: { analysis: TimeframeAnalysisOut; title: string } = $props();

	const trendColor = {
		bullish: 'text-emerald-600 dark:text-emerald-400',
		bearish: 'text-rose-600 dark:text-rose-400',
		neutral: 'text-slate-500'
	} as const;

	const regimeColor = {
		trending: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300',
		ranging: 'bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-300',
		transitioning: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300'
	} as const;

	const patternLabel = {
		doji: 'Doji',
		hammer: 'Hammer',
		shooting_star: 'Shooting Star',
		bullish_engulfing: 'Bullish Engulfing',
		bearish_engulfing: 'Bearish Engulfing'
	} as const;

	const patternColor = {
		bullish: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
		bearish: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
		neutral: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
	} as const;
</script>

<div class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
	<div class="mb-3 flex items-center justify-between">
		<h3 class="font-medium">{title} · {analysis.timeframe}</h3>
		<div class="flex gap-2">
			<span class="text-sm font-semibold capitalize {trendColor[analysis.trend]}"
				>{analysis.trend}</span
			>
			<span
				class="rounded-full px-2 py-0.5 text-xs font-medium capitalize {regimeColor[
					analysis.regime
				]}"
			>
				{analysis.regime}
			</span>
			{#if analysis.candlestick_pattern && analysis.candlestick_pattern_bias}
				<span
					class="rounded-full px-2 py-0.5 text-xs font-medium {patternColor[
						analysis.candlestick_pattern_bias
					]}"
				>
					{patternLabel[analysis.candlestick_pattern]}
				</span>
			{/if}
		</div>
	</div>

	<dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-3">
		<div>
			<dt class="text-slate-400">Last close</dt>
			<dd class="tabular-nums">{formatPrice(analysis.last_close)}</dd>
		</div>
		<div>
			<dt class="text-slate-400">EMA 20 / 50 / 200</dt>
			<dd class="tabular-nums">
				{formatPrice(analysis.ema_20)} / {formatPrice(analysis.ema_50)} / {formatPrice(
					analysis.ema_200
				)}
			</dd>
		</div>
		<div>
			<dt class="text-slate-400">RSI 14</dt>
			<dd class="tabular-nums">{analysis.rsi_14?.toFixed(1) ?? '—'}</dd>
		</div>
		<div>
			<dt class="text-slate-400">ATR 14</dt>
			<dd class="tabular-nums">{formatPrice(analysis.atr_14)}</dd>
		</div>
		<div>
			<dt class="text-slate-400">ADX 14</dt>
			<dd class="tabular-nums">{analysis.adx_14?.toFixed(1) ?? '—'}</dd>
		</div>
		<div>
			<dt class="text-slate-400">Support</dt>
			<dd class="tabular-nums">
				{analysis.support_levels.map((v) => formatPrice(v)).join(', ') || '—'}
			</dd>
		</div>
		<div>
			<dt class="text-slate-400">Resistance</dt>
			<dd class="tabular-nums">
				{analysis.resistance_levels.map((v) => formatPrice(v)).join(', ') || '—'}
			</dd>
		</div>
	</dl>
</div>
