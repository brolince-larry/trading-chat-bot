<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import type { PriceOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { formatDateTime, formatPrice } from '$lib/format';

	let prices = $state<Record<string, PriceOut>>({});
	let live = $state(false);
	let lastUpdated = $state<string | null>(null);

	const symbols = $derived(Object.keys(prices).sort());

	onMount(() => {
		return connectLiveSocket<Record<string, PriceOut>>(
			'/ws/prices',
			(data) => {
				prices = data;
				lastUpdated = new Date().toISOString();
			},
			{
				onOpen: () => (live = true),
				onClose: () => (live = false)
			}
		);
	});
</script>

<svelte:head><title>Live Prices — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-4">
	<div class="flex items-center gap-2">
		<h1 class="text-xl font-semibold">Live Prices</h1>
		<span class="flex items-center gap-1.5 text-xs text-slate-500">
			<span
				class="h-2 w-2 rounded-full {live ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}"
			></span>
			{live ? 'Live' : 'Connecting…'}
		</span>
	</div>
	{#if lastUpdated}
		<p class="text-sm text-slate-500">Last tick: {formatDateTime(lastUpdated)}</p>
	{/if}

	{#if symbols.length === 0}
		<p class="text-sm text-slate-500">Waiting for the first price tick…</p>
	{:else}
		<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
			{#each symbols as symbol (symbol)}
				{@const price = prices[symbol]}
				<a
					href={resolve('/analysis/[symbol]', { symbol })}
					class="rounded border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
				>
					<p class="text-sm font-medium">{symbol}</p>
					<div class="mt-2 flex items-baseline justify-between">
						<span class="text-xs text-slate-400">Bid</span>
						<span class="tabular-nums">{formatPrice(price.bid)}</span>
					</div>
					<div class="flex items-baseline justify-between">
						<span class="text-xs text-slate-400">Ask</span>
						<span class="tabular-nums">{formatPrice(price.ask)}</span>
					</div>
					<div class="mt-1 flex items-baseline justify-between text-xs text-slate-400">
						<span>Spread</span>
						<span class="tabular-nums">{Number(price.spread_pips).toFixed(1)} pips</span>
					</div>
				</a>
			{/each}
		</div>
	{/if}
</div>
