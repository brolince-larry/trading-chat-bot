<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { PositionOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { directionColor, formatDateTime, formatMoney, formatPrice, pnlColor } from '$lib/format';

	let positions = $state<PositionOut[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let live = $state(false);
	let closingId = $state<string | null>(null);

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
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not close the position.';
		} finally {
			closingId = null;
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

<svelte:head><title>Positions — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-4">
	<div class="flex items-center gap-2">
		<h1 class="text-xl font-semibold">Open Positions</h1>
		<span class="flex items-center gap-1.5 text-xs text-slate-500">
			<span
				class="h-2 w-2 rounded-full {live ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-700'}"
			></span>
			{live ? 'Live' : 'Connecting…'}
		</span>
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
			No open positions. Open one from a confirmed setup on the Scanner page.
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
						<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/60">
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
									onclick={() => closePosition(position.id)}
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
	{/if}
</div>
