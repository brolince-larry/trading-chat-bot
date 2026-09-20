<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { ExposureLevel } from '$lib/api/types';

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let saved = $state(false);

	let maxRiskPerTradePercent = $state(1);
	let maxDailyLossPercent = $state(3);
	let maxOpenPositions = $state(5);
	let maxSpreadPips = $state(3);
	let maxCorrelatedExposure = $state<ExposureLevel>('medium');
	let minRiskReward = $state('1.5');
	let maxDrawdownPercent = $state(10);

	onMount(async () => {
		try {
			const limits = await api.getRiskLimits();
			maxRiskPerTradePercent = Number(limits.max_risk_per_trade_percent);
			maxDailyLossPercent = Number(limits.max_daily_loss_percent);
			maxOpenPositions = limits.max_open_positions;
			maxSpreadPips = Number(limits.max_spread_pips);
			maxCorrelatedExposure = limits.max_correlated_exposure;
			minRiskReward = limits.min_risk_reward ?? '';
			maxDrawdownPercent = limits.max_drawdown_percent ? Number(limits.max_drawdown_percent) : 10;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load risk limits.';
		} finally {
			loading = false;
		}
	});

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		saving = true;
		error = null;
		saved = false;
		try {
			await api.updateRiskLimits({
				max_risk_per_trade_percent: String(maxRiskPerTradePercent),
				max_daily_loss_percent: String(maxDailyLossPercent),
				max_open_positions: maxOpenPositions,
				max_spread_pips: String(maxSpreadPips),
				max_correlated_exposure: maxCorrelatedExposure,
				min_risk_reward: minRiskReward || null,
				max_drawdown_percent: String(maxDrawdownPercent)
			});
			saved = true;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not save risk limits.';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Risk Management — Forex AI Market Scanner</title></svelte:head>

<div class="max-w-2xl">
	<h1 class="mb-1 text-xl font-semibold">Risk Management</h1>
	<p class="mb-6 text-sm text-slate-500">
		These limits are enforced by the risk-validation engine before a trade is sized or opened — not
		left to discipline in the moment.
	</p>

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else}
		<form onsubmit={submit} class="flex flex-col gap-6">
			<div class="grid gap-6 sm:grid-cols-2">
				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<div class="mb-2 flex items-baseline justify-between">
						<span class="text-sm font-medium">Risk Per Trade</span>
						<span class="text-sm font-semibold tabular-nums">{maxRiskPerTradePercent}%</span>
					</div>
					<input
						type="range"
						min="0.1"
						max="10"
						step="0.1"
						bind:value={maxRiskPerTradePercent}
						class="w-full"
					/>
					<p class="mt-1 text-xs text-slate-400">Recommended 0.5% – 2%</p>
				</div>

				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<div class="mb-2 flex items-baseline justify-between">
						<span class="text-sm font-medium">Daily Loss Limit</span>
						<span class="text-sm font-semibold tabular-nums">{maxDailyLossPercent}%</span>
					</div>
					<input
						type="range"
						min="1"
						max="20"
						step="0.5"
						bind:value={maxDailyLossPercent}
						class="w-full"
					/>
					<p class="mt-1 text-xs text-slate-400">Stop trading if today's loss exceeds this</p>
				</div>

				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<div class="mb-2 flex items-baseline justify-between">
						<span class="text-sm font-medium">Max Open Trades</span>
						<span class="text-sm font-semibold tabular-nums">{maxOpenPositions}</span>
					</div>
					<input
						type="range"
						min="1"
						max="20"
						step="1"
						bind:value={maxOpenPositions}
						class="w-full"
					/>
					<p class="mt-1 text-xs text-slate-400">Current cap on simultaneous positions</p>
				</div>

				<div
					class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
				>
					<div class="mb-2 flex items-baseline justify-between">
						<span class="text-sm font-medium">Drawdown Limit</span>
						<span class="text-sm font-semibold tabular-nums">{maxDrawdownPercent}%</span>
					</div>
					<input
						type="range"
						min="1"
						max="50"
						step="1"
						bind:value={maxDrawdownPercent}
						class="w-full"
					/>
					<p class="mt-1 text-xs text-slate-400">
						Max peak-to-trough equity drop (informational — see Dashboard equity curve)
					</p>
				</div>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<label class="flex flex-col gap-1 text-sm">
					Max spread (pips)
					<input
						type="number"
						step="any"
						required
						bind:value={maxSpreadPips}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
				<label class="flex flex-col gap-1 text-sm">
					Max correlated exposure
					<select
						bind:value={maxCorrelatedExposure}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					>
						<option value="low">Low</option>
						<option value="medium">Medium</option>
						<option value="high">High</option>
					</select>
				</label>
			</div>

			<label class="flex flex-col gap-1 text-sm">
				Min risk/reward (optional)
				<input
					type="number"
					step="any"
					bind:value={minRiskReward}
					class="max-w-xs rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
				/>
			</label>

			{#if error}
				<div
					class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
				>
					{error}
				</div>
			{/if}
			{#if saved}
				<div
					class="rounded border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-300"
				>
					Saved.
				</div>
			{/if}

			<button
				type="submit"
				disabled={saving}
				class="w-fit rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{saving ? 'Saving…' : 'Save Limits'}
			</button>
		</form>
	{/if}
</div>
