<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { api, ApiError } from '$lib/api/client';
	import type { PerformanceStatsOut, PositionOut, ScanResultOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { formatMoney, pnlColor } from '$lib/format';
	import ExposureChart from '$lib/components/ExposureChart.svelte';

	let openPositions = $state<PositionOut[]>([]);
	let stats = $state<PerformanceStatsOut | null>(null);
	let scan = $state<ScanResultOut | null>(null);
	let error = $state<string | null>(null);
	let loading = $state(true);

	const unrealizedTotal = $derived(
		openPositions.reduce((sum, p) => sum + (p.unrealized_pnl ? Number(p.unrealized_pnl) : 0), 0)
	);
	const activeSetups = $derived(
		scan ? scan.candidates.filter((c) => c.setup.status !== 'rejected').length : 0
	);
	const confirmedSetups = $derived(
		scan ? scan.candidates.filter((c) => c.setup.status === 'confirmed').length : 0
	);

	onMount(() => {
		Promise.all([api.listPositions('open'), api.getPositionStats(), api.runScan()])
			.then(([positions, performance, scanResult]) => {
				openPositions = positions;
				stats = performance;
				scan = scanResult;
			})
			.catch((err) => {
				error = err instanceof ApiError ? err.message : 'Could not load the overview.';
			})
			.finally(() => {
				loading = false;
			});

		const stopPositions = connectLiveSocket<PositionOut[]>('/ws/positions', (data) => {
			openPositions = data;
		});
		const stopScanner = connectLiveSocket<ScanResultOut>('/ws/scanner', (data) => {
			scan = data;
		});
		return () => {
			stopPositions();
			stopScanner();
		};
	});
</script>

<svelte:head><title>Overview — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-6">
	<h1 class="text-xl font-semibold">Overview</h1>

	{#if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{/if}

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else}
		<div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
			<a
				href={resolve('/positions')}
				class="rounded border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
			>
				<p class="text-xs text-slate-400">Open positions</p>
				<p class="text-2xl font-semibold tabular-nums">{openPositions.length}</p>
			</a>
			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<p class="text-xs text-slate-400">Unrealized P&L</p>
				<p class="text-2xl font-semibold tabular-nums {pnlColor(unrealizedTotal)}">
					{formatMoney(unrealizedTotal)}
				</p>
			</div>
			<a
				href={resolve('/history')}
				class="rounded border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
			>
				<p class="text-xs text-slate-400">Total realized P&L</p>
				<p
					class="text-2xl font-semibold tabular-nums {pnlColor(stats?.total_realized_pnl ?? null)}"
				>
					{stats ? formatMoney(stats.total_realized_pnl) : '—'}
				</p>
			</a>
			<a
				href={resolve('/scanner')}
				class="rounded border border-slate-200 bg-white p-4 transition-colors hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700"
			>
				<p class="text-xs text-slate-400">Active setups</p>
				<p class="text-2xl font-semibold tabular-nums">
					{activeSetups}
					<span class="text-sm font-normal text-slate-400">({confirmedSetups} confirmed)</span>
				</p>
			</a>
		</div>

		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-medium text-slate-500">Currency Exposure</h2>
			<ExposureChart exposures={scan?.currency_exposure ?? []} />
		</div>
	{/if}
</div>
