<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { PerformanceStatsOut, PositionOut } from '$lib/api/types';
	import {
		directionColor,
		formatDateTime,
		formatMoney,
		formatPercent,
		formatPrice,
		pnlColor,
		positionStatusLabel
	} from '$lib/format';

	let positions = $state<PositionOut[]>([]);
	let stats = $state<PerformanceStatsOut | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let tab = $state<'overview' | 'history'>('overview');
	let fromDate = $state('');
	let toDate = $state('');

	const filteredPositions = $derived(
		positions.filter((p) => {
			if (!p.closed_at) return false;
			const closed = p.closed_at.slice(0, 10);
			if (fromDate && closed < fromDate) return false;
			if (toDate && closed > toDate) return false;
			return true;
		})
	);

	onMount(async () => {
		try {
			[positions, stats] = await Promise.all([api.listPositions('closed'), api.getPositionStats()]);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load trade history.';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head><title>Reports — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-6">
	<h1 class="text-xl font-semibold">Reports</h1>

	<div class="flex gap-1 border-b border-slate-200 dark:border-slate-800">
		<button
			onclick={() => (tab = 'overview')}
			class="border-b-2 px-3 py-2 text-sm font-medium {tab === 'overview'
				? 'border-slate-900 dark:border-white'
				: 'border-transparent text-slate-500'}"
		>
			Overview
		</button>
		<button
			onclick={() => (tab = 'history')}
			class="border-b-2 px-3 py-2 text-sm font-medium {tab === 'history'
				? 'border-slate-900 dark:border-white'
				: 'border-transparent text-slate-500'}"
		>
			Trade History
		</button>
	</div>

	{#if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{/if}

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else if tab === 'overview'}
		{#if stats}
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-5">
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Total Trades</p>
					<p class="text-lg font-semibold tabular-nums">{stats.closed_count}</p>
				</div>
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Winning Trades</p>
					<p class="text-lg font-semibold text-emerald-600 tabular-nums dark:text-emerald-400">
						{stats.win_count} ({stats.win_rate !== null
							? formatPercent(stats.win_rate * 100)
							: '—'})
					</p>
				</div>
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Losing Trades</p>
					<p class="text-lg font-semibold text-rose-600 tabular-nums dark:text-rose-400">
						{stats.loss_count}
					</p>
				</div>
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Total Profit</p>
					<p class="text-lg font-semibold tabular-nums {pnlColor(stats.total_realized_pnl)}">
						{formatMoney(stats.total_realized_pnl)}
					</p>
				</div>
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Profit Factor</p>
					<p class="text-lg font-semibold tabular-nums">
						{stats.profit_factor !== null ? stats.profit_factor.toFixed(2) : '—'}
					</p>
				</div>
			</div>
			<div class="grid grid-cols-2 gap-4 sm:grid-cols-3">
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Expectancy</p>
					<p class="text-lg font-semibold tabular-nums">
						{stats.expectancy_r !== null ? `${stats.expectancy_r.toFixed(2)}R` : '—'}
					</p>
				</div>
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<p class="text-xs text-slate-400">Average R-Multiple</p>
					<p class="text-lg font-semibold tabular-nums">
						{stats.average_r_multiple !== null ? `${stats.average_r_multiple.toFixed(2)}R` : '—'}
					</p>
				</div>
			</div>
		{/if}
	{:else}
		<div class="flex flex-wrap items-end gap-3">
			<label class="flex flex-col gap-1 text-xs text-slate-500">
				From
				<input
					type="date"
					bind:value={fromDate}
					class="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
				/>
			</label>
			<label class="flex flex-col gap-1 text-xs text-slate-500">
				To
				<input
					type="date"
					bind:value={toDate}
					class="rounded border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
				/>
			</label>
			{#if fromDate || toDate}
				<button
					onclick={() => {
						fromDate = '';
						toDate = '';
					}}
					class="rounded border border-slate-300 px-2 py-1 text-xs hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
				>
					Clear
				</button>
			{/if}
		</div>

		{#if filteredPositions.length === 0}
			<p
				class="rounded border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900"
			>
				No closed trades {fromDate || toDate ? 'in this date range' : 'yet'}.
			</p>
		{:else}
			<div class="overflow-x-auto rounded border border-slate-200 dark:border-slate-800">
				<table class="w-full min-w-[900px] text-sm">
					<thead class="bg-slate-100 text-left text-xs text-slate-500 uppercase dark:bg-slate-900">
						<tr>
							<th class="px-3 py-2">Pair</th>
							<th class="px-3 py-2">Direction</th>
							<th class="px-3 py-2">Entry</th>
							<th class="px-3 py-2">Exit</th>
							<th class="px-3 py-2">Closed by</th>
							<th class="px-3 py-2">R multiple</th>
							<th class="px-3 py-2">Realized P&L</th>
							<th class="px-3 py-2">Closed</th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-200 dark:divide-slate-800">
						{#each filteredPositions as position (position.id)}
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/60">
								<td class="px-3 py-2 font-medium">{position.symbol}</td>
								<td class="px-3 py-2 font-medium capitalize {directionColor(position.direction)}">
									{position.direction}
								</td>
								<td class="px-3 py-2 tabular-nums">{formatPrice(position.entry_price)}</td>
								<td class="px-3 py-2 tabular-nums">{formatPrice(position.close_price)}</td>
								<td class="px-3 py-2 text-slate-500 capitalize">
									{positionStatusLabel(position.status)}
								</td>
								<td class="px-3 py-2 tabular-nums">
									{position.risk_multiple ? `${Number(position.risk_multiple).toFixed(2)}R` : '—'}
								</td>
								<td class="px-3 py-2 font-medium tabular-nums {pnlColor(position.realized_pnl)}">
									{formatMoney(position.realized_pnl)}
									{position.account_currency}
								</td>
								<td class="px-3 py-2 text-xs text-slate-500">
									{position.closed_at ? formatDateTime(position.closed_at) : '—'}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}
</div>
