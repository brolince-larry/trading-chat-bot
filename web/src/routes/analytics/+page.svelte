<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { CurrencyExposureOut, PositionOut } from '$lib/api/types';
	import { pnlColor } from '$lib/format';
	import { groupByOutcome } from '$lib/helpers';
	import ExposureChart from '$lib/components/ExposureChart.svelte';

	let positions = $state<PositionOut[]>([]);
	let currencyExposure = $state<CurrencyExposureOut[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function pnlOf(p: PositionOut): number {
		return p.realized_pnl ? Number(p.realized_pnl) : 0;
	}

	const byStrategy = $derived(
		groupByOutcome(positions, (p) => p.strategy.replace('_', ' '), pnlOf)
	);
	const byPair = $derived(groupByOutcome(positions, (p) => p.symbol, pnlOf));

	const R_BUCKETS = [
		{ label: '< -1R', test: (r: number) => r < -1 },
		{ label: '-1R to 0', test: (r: number) => r >= -1 && r < 0 },
		{ label: '0 to 1R', test: (r: number) => r >= 0 && r < 1 },
		{ label: '1R to 2R', test: (r: number) => r >= 1 && r < 2 },
		{ label: '>= 2R', test: (r: number) => r >= 2 }
	];

	const rDistribution = $derived(
		R_BUCKETS.map((bucket) => ({
			label: bucket.label,
			count: positions.filter(
				(p) => p.risk_multiple !== null && bucket.test(Number(p.risk_multiple))
			).length
		}))
	);
	const maxRCount = $derived(Math.max(1, ...rDistribution.map((b) => b.count)));

	onMount(async () => {
		try {
			const [closed, scan] = await Promise.all([api.listPositions('closed'), api.runScan()]);
			positions = closed;
			currencyExposure = scan.currency_exposure;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load analytics.';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head><title>Analytics — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="text-xl font-semibold">Analytics</h1>
		<p class="text-sm text-slate-500">
			Performance breakdowns derived entirely from your closed paper trades.
		</p>
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
	{:else if positions.length === 0}
		<p
			class="rounded border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900"
		>
			No closed trades yet — analytics will populate as positions close.
		</p>
	{:else}
		<div class="grid gap-4 lg:grid-cols-2">
			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<h2 class="mb-3 text-sm font-semibold">Win Rate by Strategy</h2>
				<div class="flex flex-col gap-2">
					{#each byStrategy as group (group.key)}
						<div class="flex items-center justify-between text-sm">
							<span class="capitalize">{group.key}</span>
							<span class="text-slate-500 tabular-nums">
								{group.wins}/{group.total} ({((group.wins / group.total) * 100).toFixed(0)}%)
							</span>
							<span class="tabular-nums {pnlColor(group.pnl)}"
								>{group.pnl >= 0 ? '+' : ''}{group.pnl.toFixed(2)}</span
							>
						</div>
					{/each}
				</div>
			</div>

			<div
				class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
			>
				<h2 class="mb-3 text-sm font-semibold">Win Rate by Pair</h2>
				<div class="flex flex-col gap-2">
					{#each byPair as group (group.key)}
						<div class="flex items-center justify-between text-sm">
							<span>{group.key}</span>
							<span class="text-slate-500 tabular-nums">
								{group.wins}/{group.total} ({((group.wins / group.total) * 100).toFixed(0)}%)
							</span>
							<span class="tabular-nums {pnlColor(group.pnl)}"
								>{group.pnl >= 0 ? '+' : ''}{group.pnl.toFixed(2)}</span
							>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-semibold">R-Multiple Distribution</h2>
			<div class="flex flex-col gap-2">
				{#each rDistribution as bucket (bucket.label)}
					<div class="flex items-center gap-3 text-sm">
						<span class="w-20 shrink-0 text-slate-500">{bucket.label}</span>
						<div class="h-4 flex-1 rounded bg-slate-100 dark:bg-slate-800">
							<div
								class="h-4 rounded bg-sky-500"
								style="width: {(bucket.count / maxRCount) * 100}%"
							></div>
						</div>
						<span class="w-6 text-right tabular-nums">{bucket.count}</span>
					</div>
				{/each}
			</div>
		</div>

		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-semibold">Currency Exposure (current scan)</h2>
			<ExposureChart exposures={currencyExposure} />
		</div>
	{/if}
</div>
