<script lang="ts">
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { api, ApiError } from '$lib/api/client';
	import type { PairAnalysisOut } from '$lib/api/types';
	import TimeframeCard from '$lib/components/TimeframeCard.svelte';

	let analysis = $state<PairAnalysisOut | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	$effect(() => {
		const symbol = page.params.symbol;
		if (!symbol) {
			error = 'No symbol was given.';
			loading = false;
			return;
		}
		loading = true;
		error = null;
		analysis = null;

		api
			.getPairAnalysis(symbol)
			.then((data) => {
				analysis = data;
			})
			.catch((err) => {
				error = err instanceof ApiError ? err.message : 'Could not load analysis for this pair.';
			})
			.finally(() => {
				loading = false;
			});
	});
</script>

<svelte:head><title>{page.params.symbol} analysis — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-4">
	<div class="flex items-center gap-3">
		<a href={resolve('/')} class="text-sm text-slate-500 hover:underline">&larr; Scanner</a>
		<h1 class="text-xl font-semibold">{page.params.symbol}</h1>
	</div>

	{#if loading}
		<p class="text-sm text-slate-500">Loading analysis…</p>
	{:else if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{:else if analysis}
		<div class="grid gap-4 md:grid-cols-2">
			<TimeframeCard analysis={analysis.higher_timeframe} title="Higher timeframe" />
			<TimeframeCard analysis={analysis.entry_timeframe} title="Entry timeframe" />
		</div>
	{/if}
</div>
