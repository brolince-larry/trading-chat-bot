<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { PositionOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { directionColor, formatDateTime, formatMoney, formatPrice, pnlColor } from '$lib/format';
	import CandlestickChart from '$lib/components/CandlestickChart.svelte';

	let positions = $state<PositionOut[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let live = $state(false);
	let closingId = $state<string | null>(null);
	let closingAll = $state(false);
	let selectedId = $state<string | null>(null);

	const selectedPosition = $derived(positions.find((p) => p.id === selectedId) ?? null);

	async function loadInitial() {
		loading = true;
		error = null;
		try {
			positions = await api.listPositions('open');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load open positions.';
		} finally {
			loading = false;
		}
	}

	async function closePosition(id: string) {
		closingId = id;
		try {
			await api.closePosition(id);
			positions = positions.filter((p) => p.id !== id);
			if (selectedId === id) selectedId = null;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not close the position.';
		} finally {
			closingId = null;
		}
	}

	async function closeAll() {
		closingAll = true;
		error = null;
		try {
			await api.closeAllPositions();
			positions = [];
			selectedId = null;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not close all positions.';
		} finally {
			closingAll = false;
		}
	}

	onMount(() => {
		loadInitial();
		return connectLiveSocket<PositionOut[]>(
			'/ws/positions',
			(data) => {
				positions = data;
			},
			{
				onOpen: () => (live = true),
				onClose: () => (live = false)
			}
		);
	});
</script>

<svelte:head><title>Portfolio — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-4">
	<div class="flex flex-wrap items-center justify-between gap-3">
		<div class="flex items-center gap-2">
			<h1 class="text-xl font-semibold">Portfolio</h1>
			<span class="flex items-center gap-1.5 text-xs text-slate-500">
				<span
					class="h-2 w-2 rounded-full {live ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}"
				></span>
				{live ? 'Live' : 'Connecting…'}
			</span>
		</div>
		{#if positions.length > 0}
			<button
				onclick={closeAll}
				disabled={closingAll}
				class="rounded bg-rose-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-rose-700 disabled:opacity-50"
			>
				{closingAll ? 'Closing…' : 'Close All Trades'}
			</button>
		{/if}
	</div>
	<p class="text-sm text-slate-500">
		Paper positions are tracked continuously and close automatically when price touches their
		stop-loss or take-profit — no manual polling required.
	</p>

	{#if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{/if}

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else if positions.length === 0}
		<p
			class="rounded border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900"
		>
			No open positions. Open one from the Markets page or the Trade panel on a pair's Analysis
			page.
		</p>
	{:else}
		<div class="overflow-x-auto rounded border border-slate-200 dark:border-slate-800">
			<table class="w-full min-w-[900px] text-sm">
				<thead class="bg-slate-100 text-left text-xs text-slate-500 uppercase dark:bg-slate-900">
					<tr>
						<th class="px-3 py-2">Pair</th>
						<th class="px-3 py-2">Direction</th>
						<th class="px-3 py-2">Size</th>
						<th class="px-3 py-2">Entry</th>
						<th class="px-3 py-2">Stop</th>
						<th class="px-3 py-2">Target</th>
						<th class="px-3 py-2">Unrealized P&L</th>
						<th class="px-3 py-2">Opened</th>
						<th class="px-3 py-2"></th>
					</tr>
				</thead>
				<tbody class="divide-y divide-slate-200 dark:divide-slate-800">
					{#each positions as position (position.id)}
						<tr
							onclick={() => (selectedId = position.id)}
							class="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-900/60 {selectedId ===
							position.id
								? 'bg-slate-50 dark:bg-slate-900/60'
								: ''}"
						>
							<td class="px-3 py-2 font-medium">{position.symbol}</td>
							<td class="px-3 py-2 font-medium capitalize {directionColor(position.direction)}">
								{position.direction}
							</td>
							<td class="px-3 py-2 tabular-nums">{position.lots} lots</td>
							<td class="px-3 py-2 tabular-nums">{formatPrice(position.entry_price)}</td>
							<td class="px-3 py-2 tabular-nums">{formatPrice(position.stop_loss)}</td>
							<td class="px-3 py-2 tabular-nums">{formatPrice(position.take_profit)}</td>
							<td class="px-3 py-2 font-medium tabular-nums {pnlColor(position.unrealized_pnl)}">
								{formatMoney(position.unrealized_pnl)}
								{position.account_currency}
							</td>
							<td class="px-3 py-2 text-xs text-slate-500">{formatDateTime(position.opened_at)}</td>
							<td class="px-3 py-2">
								<button
									onclick={(e) => {
										e.stopPropagation();
										closePosition(position.id);
									}}
									disabled={closingId === position.id}
									class="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
								>
									{closingId === position.id ? 'Closing…' : 'Close'}
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		{#if selectedPosition}
			<div class="grid gap-4 lg:grid-cols-3">
				<div
					class="rounded border border-slate-200 bg-white p-3 lg:col-span-2 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="mb-2 text-xs text-slate-500">Live chart — {selectedPosition.symbol}</p>
					<CandlestickChart
						symbol={selectedPosition.symbol}
						timeframe="1h"
						entryPrice={Number(selectedPosition.entry_price)}
						stopLoss={Number(selectedPosition.stop_loss)}
						takeProfit={selectedPosition.take_profit ? Number(selectedPosition.take_profit) : null}
						height={280}
					/>
				</div>
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<h2 class="mb-3 text-sm font-semibold">Trade Details</h2>
					<dl class="flex flex-col gap-2 text-sm">
						<div class="flex justify-between">
							<dt class="text-slate-400">Symbol</dt>
							<dd>{selectedPosition.symbol}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-400">Type</dt>
							<dd class="capitalize {directionColor(selectedPosition.direction)}">
								{selectedPosition.direction}
							</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-400">Lot Size</dt>
							<dd>{selectedPosition.lots}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-400">Entry</dt>
							<dd class="tabular-nums">{formatPrice(selectedPosition.entry_price)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-400">Stop</dt>
							<dd class="tabular-nums">{formatPrice(selectedPosition.stop_loss)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-400">Target</dt>
							<dd class="tabular-nums">{formatPrice(selectedPosition.take_profit)}</dd>
						</div>
						<div class="flex justify-between">
							<dt class="text-slate-400">P&amp;L</dt>
							<dd class="font-semibold tabular-nums {pnlColor(selectedPosition.unrealized_pnl)}">
								{formatMoney(selectedPosition.unrealized_pnl)}
							</dd>
						</div>
					</dl>
				</div>
			</div>
		{/if}
	{/if}
</div>
