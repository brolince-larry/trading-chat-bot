<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { api, ApiError } from '$lib/api/client';
	import type { AccountRange, AccountSummaryOut, ScanResultOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { formatMoney, formatPercent, pnlColor } from '$lib/format';
	import ExposureChart from '$lib/components/ExposureChart.svelte';
	import EquityChart from '$lib/components/EquityChart.svelte';

	const RANGES: { key: AccountRange; label: string }[] = [
		{ key: '1d', label: '1D' },
		{ key: '1w', label: '1W' },
		{ key: '1m', label: '1M' },
		{ key: '3m', label: '3M' },
		{ key: '6m', label: '6M' },
		{ key: '1y', label: '1Y' },
		{ key: 'all', label: 'ALL' }
	];

	let summary = $state<AccountSummaryOut | null>(null);
	let scan = $state<ScanResultOut | null>(null);
	let range = $state<AccountRange>('1m');
	let error = $state<string | null>(null);
	let loading = $state(true);

	async function loadSummary() {
		try {
			summary = await api.getAccountSummary(range);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load the account summary.';
		}
	}

	$effect(() => {
		loadSummary();
	});

	onMount(() => {
		Promise.all([api.getAccountSummary(range), api.runScan()])
			.then(([accountSummary, scanResult]) => {
				summary = accountSummary;
				scan = scanResult;
			})
			.catch((err) => {
				error = err instanceof ApiError ? err.message : 'Could not load the overview.';
			})
			.finally(() => {
				loading = false;
			});

		const stopPositions = connectLiveSocket('/ws/positions', () => loadSummary());
		const stopScanner = connectLiveSocket<ScanResultOut>('/ws/scanner', (data) => {
			scan = data;
		});
		return () => {
			stopPositions();
			stopScanner();
		};
	});
</script>

<svelte:head><title>Dashboard — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex items-center justify-between">
		<h1 class="text-xl font-semibold">Dashboard</h1>
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
	{:else if summary}
		<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<p class="text-xs text-slate-400">Account Balance</p>
				<p class="text-2xl font-semibold tabular-nums">{formatMoney(summary.balance, 2)}</p>
				<p class="text-xs tabular-nums {pnlColor(summary.total_pnl_percent)}">
					{summary.total_pnl_percent >= 0 ? '+' : ''}{summary.total_pnl_percent.toFixed(2)}%
					all-time
				</p>
			</div>
			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<p class="text-xs text-slate-400">Total Profit/Loss</p>
				<p class="text-2xl font-semibold tabular-nums {pnlColor(summary.total_realized_pnl)}">
					{formatMoney(summary.total_realized_pnl)}
				</p>
				<p class="text-xs text-slate-400">
					Unrealized: <span class={pnlColor(summary.total_unrealized_pnl)}
						>{formatMoney(summary.total_unrealized_pnl)}</span
					>
				</p>
			</div>
			<a
				href={resolve('/positions')}
				class="rounded border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
			>
				<p class="text-xs text-slate-400">Active Trades</p>
				<p class="text-2xl font-semibold tabular-nums">{summary.active_trades}</p>
			</a>
			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<p class="text-xs text-slate-400">Win Rate</p>
				<p class="text-2xl font-semibold tabular-nums">
					{formatPercent(summary.win_rate ? summary.win_rate * 100 : null)}
				</p>
			</div>
		</div>

		<div class="grid gap-4 lg:grid-cols-3">
			<div
				class="rounded border border-slate-200 bg-white p-4 lg:col-span-2 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="mb-3 flex items-center justify-between">
					<h2 class="text-sm font-medium text-slate-500">Account Growth</h2>
					<div class="flex gap-1">
						{#each RANGES as r (r.key)}
							<button
								onclick={() => (range = r.key)}
								class="rounded px-2 py-1 text-xs font-medium {range === r.key
									? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
									: 'text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'}"
							>
								{r.label}
							</button>
						{/each}
					</div>
				</div>
				<EquityChart points={summary.equity_curve} />
			</div>

			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<h2 class="mb-3 text-sm font-medium text-slate-500">Top Performing Pairs</h2>
				{#if summary.top_pairs.length === 0}
					<p class="text-sm text-slate-400">No closed trades yet.</p>
				{:else}
					<ul class="flex flex-col gap-2.5">
						{#each summary.top_pairs as pair (pair.symbol)}
							<li class="flex items-center justify-between text-sm">
								<a
									href={resolve('/analysis/[symbol]', { symbol: pair.symbol })}
									class="font-medium hover:underline"
								>
									{pair.symbol}
								</a>
								<span class="tabular-nums {pnlColor(pair.realized_pnl)}"
									>{formatMoney(pair.realized_pnl)}</span
								>
							</li>
						{/each}
					</ul>
				{/if}
			</div>
		</div>

		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-medium text-slate-500">Currency Exposure</h2>
			<ExposureChart exposures={scan?.currency_exposure ?? []} />
		</div>
	{/if}
</div>
