<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { api, ApiError } from '$lib/api/client';
	import type { PairAnalysisOut, PositionOut, ScanResultOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import TimeframeCard from '$lib/components/TimeframeCard.svelte';
	import CandlestickChart from '$lib/components/CandlestickChart.svelte';
	import TradePanel from '$lib/components/TradePanel.svelte';
	import SessionClock from '$lib/components/SessionClock.svelte';
	import NewsPanel from '$lib/components/NewsPanel.svelte';

	const TIMEFRAMES = ['15m', '1h', '4h', '1d'] as const;

	let analysis = $state<PairAnalysisOut | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let chartTimeframe = $state<(typeof TIMEFRAMES)[number]>('1h');
	let scanResult = $state<ScanResultOut | null>(null);
	let openPosition = $state<PositionOut | null>(null);

	const symbol = $derived(page.params.symbol ?? '');

	const symbolCandidate = $derived(
		scanResult?.candidates.find((c) => c.setup.symbol === symbol) ?? null
	);

	const bestCandidate = $derived(
		scanResult
			? [...scanResult.candidates]
					.filter((c) => c.setup.status === 'confirmed')
					.sort((a, b) => b.quality_score - a.quality_score)[0]
			: null
	);

	const chartLevels = $derived.by(() => {
		if (openPosition) {
			return {
				entry: Number(openPosition.entry_price),
				stop: Number(openPosition.stop_loss),
				target: openPosition.take_profit ? Number(openPosition.take_profit) : null
			};
		}
		if (symbolCandidate?.setup.entry_price != null && symbolCandidate.setup.stop_loss != null) {
			return {
				entry: symbolCandidate.setup.entry_price,
				stop: symbolCandidate.setup.stop_loss,
				target: symbolCandidate.setup.take_profits[0]?.price ?? null
			};
		}
		return { entry: null, stop: null, target: null };
	});

	async function loadAnalysis(currentSymbol: string) {
		loading = true;
		error = null;
		analysis = null;
		try {
			analysis = await api.getPairAnalysis(currentSymbol);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load analysis for this pair.';
		} finally {
			loading = false;
		}
	}

	async function refreshOpenPosition(currentSymbol: string) {
		try {
			const open = await api.listPositions('open');
			openPosition = open.find((p) => p.symbol === currentSymbol) ?? null;
		} catch {
			// Non-fatal — the chart just falls back to the scanned setup's levels.
		}
	}

	$effect(() => {
		const currentSymbol = symbol;
		if (!currentSymbol) {
			error = 'No symbol was given.';
			loading = false;
			return;
		}
		loadAnalysis(currentSymbol);
		refreshOpenPosition(currentSymbol);
	});

	onMount(() => {
		api.runScan().then((result) => (scanResult = result));
		return connectLiveSocket<ScanResultOut>('/ws/scanner', (data) => {
			scanResult = data;
		});
	});
</script>

<svelte:head><title>{symbol} analysis — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-4">
	<div class="flex items-center gap-3">
		<a href={resolve('/')} class="text-sm text-slate-500 hover:underline">&larr; Scanner</a>
		<h1 class="text-xl font-semibold">{symbol}</h1>
	</div>

	{#if bestCandidate && bestCandidate.setup.symbol !== symbol}
		<a
			href={resolve('/analysis/[symbol]', { symbol: bestCandidate.setup.symbol })}
			class="rounded border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-800 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300 dark:hover:bg-emerald-900/40"
		>
			Best market to enter right now: <span class="font-semibold">{bestCandidate.setup.symbol}</span
			>
			— {bestCandidate.setup.direction} setup, quality score {bestCandidate.quality_score} &rarr;
		</a>
	{:else if bestCandidate}
		<div
			class="rounded border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
		>
			This is currently the best-scoring confirmed setup (quality score {bestCandidate.quality_score}).
		</div>
	{/if}

	{#if loading}
		<p class="text-sm text-slate-500">Loading analysis…</p>
	{:else if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{:else if analysis}
		<div class="grid gap-4 lg:grid-cols-3">
			<div class="flex flex-col gap-4 lg:col-span-2">
				<div
					class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
				>
					<div class="mb-2 flex items-center justify-between">
						<span class="text-xs text-slate-500">Candles &amp; trade levels</span>
						<div class="flex gap-1">
							{#each TIMEFRAMES as tf (tf)}
								<button
									onclick={() => (chartTimeframe = tf)}
									class="rounded px-2 py-1 text-xs font-medium {chartTimeframe === tf
										? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
										: 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}"
								>
									{tf}
								</button>
							{/each}
						</div>
					</div>
					<CandlestickChart
						{symbol}
						timeframe={chartTimeframe}
						entryPrice={chartLevels.entry}
						stopLoss={chartLevels.stop}
						takeProfit={chartLevels.target}
					/>
				</div>

				<div class="grid gap-4 md:grid-cols-2">
					<TimeframeCard analysis={analysis.higher_timeframe} title="Higher timeframe" />
					<TimeframeCard analysis={analysis.entry_timeframe} title="Entry timeframe" />
				</div>

				<SessionClock />
				<NewsPanel {symbol} />
			</div>

			<div>
				<TradePanel {symbol} />
			</div>
		</div>
	{/if}
</div>
