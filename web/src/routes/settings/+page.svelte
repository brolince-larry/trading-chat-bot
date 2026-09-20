<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { ExposureLevel } from '$lib/api/types';

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let saved = $state(false);

	let maxRiskPerTradePercent = $state('1');
	let maxDailyLossPercent = $state('3');
	let maxOpenPositions = $state('5');
	let maxSpreadPips = $state('3');
	let maxCorrelatedExposure = $state<ExposureLevel>('medium');
	let minRiskReward = $state('1.5');

	onMount(async () => {
		try {
			const limits = await api.getRiskLimits();
			maxRiskPerTradePercent = limits.max_risk_per_trade_percent;
			maxDailyLossPercent = limits.max_daily_loss_percent;
			maxOpenPositions = String(limits.max_open_positions);
			maxSpreadPips = limits.max_spread_pips;
			maxCorrelatedExposure = limits.max_correlated_exposure;
			minRiskReward = limits.min_risk_reward ?? '';
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
				max_risk_per_trade_percent: maxRiskPerTradePercent,
				max_daily_loss_percent: maxDailyLossPercent,
				max_open_positions: Number(maxOpenPositions),
				max_spread_pips: maxSpreadPips,
				max_correlated_exposure: maxCorrelatedExposure,
				min_risk_reward: minRiskReward || null
			});
			saved = true;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not save risk limits.';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Settings — Forex AI Market Scanner</title></svelte:head>

<div class="max-w-lg">
	<h1 class="mb-1 text-xl font-semibold">Risk Limits</h1>
	<p class="mb-4 text-sm text-slate-500">
		These limits are enforced by the risk-validation engine, not left to a human's discipline in the
		moment.
	</p>

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else}
		<form onsubmit={submit} class="flex flex-col gap-4">
			<div class="grid grid-cols-2 gap-4">
				<label class="flex flex-col gap-1 text-sm">
					Max risk per trade (%)
					<input
						type="number"
						step="any"
						required
						bind:value={maxRiskPerTradePercent}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
				<label class="flex flex-col gap-1 text-sm">
					Max daily loss (%)
					<input
						type="number"
						step="any"
						required
						bind:value={maxDailyLossPercent}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
			</div>

			<div class="grid grid-cols-2 gap-4">
				<label class="flex flex-col gap-1 text-sm">
					Max open positions
					<input
						type="number"
						step="1"
						required
						bind:value={maxOpenPositions}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
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
			</div>

			<div class="grid grid-cols-2 gap-4">
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
				<label class="flex flex-col gap-1 text-sm">
					Min risk/reward (optional)
					<input
						type="number"
						step="any"
						bind:value={minRiskReward}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
			</div>

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
				class="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{saving ? 'Saving…' : 'Save Limits'}
			</button>
		</form>
	{/if}
</div>
