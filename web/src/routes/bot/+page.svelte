<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { SymbolOut } from '$lib/api/types';
	import { toggleInSet } from '$lib/helpers';
	import BotScanPanel from '$lib/components/BotScanPanel.svelte';

	const STRATEGIES = [
		{
			name: 'trend_pullback',
			label: 'Trend Pullback',
			description: 'Enters on a pullback within an established trend, confirmed by structure.'
		},
		{
			name: 'breakout_retest',
			label: 'Breakout & Retest',
			description: 'Enters after a range breakout retests the broken level.'
		},
		{
			name: 'range_reversion',
			label: 'Range Reversion',
			description: 'Enters at range boundaries when the pair is not trending.'
		}
	];

	let symbols = $state<SymbolOut[]>([]);
	let enabled = $state(true);
	let activeSymbols = $state<Set<string>>(new Set());
	let activeStrategies = $state<Set<string>>(new Set());

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let saved = $state(false);

	function toggleSymbol(name: string) {
		activeSymbols = toggleInSet(activeSymbols, name);
	}

	function toggleStrategy(name: string) {
		activeStrategies = toggleInSet(activeStrategies, name);
	}

	onMount(async () => {
		try {
			const [botSettings, symbolList] = await Promise.all([api.getBotSettings(), api.getSymbols()]);
			enabled = botSettings.enabled;
			activeSymbols = new Set(botSettings.active_symbols);
			activeStrategies = new Set(botSettings.active_strategies);
			symbols = symbolList;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load bot settings.';
		} finally {
			loading = false;
		}
	});

	async function save() {
		if (activeSymbols.size === 0 || activeStrategies.size === 0) {
			error = 'Select at least one pair and one strategy.';
			return;
		}
		saving = true;
		error = null;
		saved = false;
		try {
			await api.updateBotSettings({
				enabled,
				active_symbols: [...activeSymbols],
				active_strategies: [...activeStrategies]
			});
			saved = true;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not save bot settings.';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Trading Bot — Forex AI Market Scanner</title></svelte:head>

<div class="flex max-w-6xl flex-col gap-6">
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-xl font-semibold">Trading Bot</h1>
			<p class="text-sm text-slate-500">
				Configure which pairs and strategies the background scanner watches. This never opens or
				closes a trade on its own — every position still requires you to click Enter Trade, Open,
				Exit, or Fire.
			</p>
		</div>
		<label class="flex items-center gap-2">
			<span class="text-sm font-medium">{enabled ? 'Bot Running' : 'Paused'}</span>
			<button
				onclick={() => (enabled = !enabled)}
				class="relative h-6 w-11 rounded-full transition-colors {enabled
					? 'bg-emerald-500'
					: 'bg-slate-300 dark:bg-slate-700'}"
				aria-label="Toggle bot running"
			>
				<span
					class="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform {enabled
						? 'translate-x-5'
						: 'translate-x-0.5'}"
				></span>
			</button>
		</label>
	</div>

	<BotScanPanel />

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else}
		<div
			class="max-w-3xl rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-semibold">Strategies</h2>
			<div class="flex flex-col gap-3">
				{#each STRATEGIES as strategy (strategy.name)}
					<label class="flex items-start gap-3 text-sm">
						<input
							type="checkbox"
							checked={activeStrategies.has(strategy.name)}
							onchange={() => toggleStrategy(strategy.name)}
							class="mt-0.5"
						/>
						<span>
							<span class="font-medium">{strategy.label}</span>
							<p class="text-xs text-slate-400">{strategy.description}</p>
						</span>
					</label>
				{/each}
			</div>
		</div>

		<div
			class="max-w-3xl rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-semibold">Trading Pairs</h2>
			<div class="flex flex-wrap gap-2">
				{#each symbols as symbol (symbol.name)}
					<button
						onclick={() => toggleSymbol(symbol.name)}
						class="rounded-full border px-3 py-1 text-xs font-medium transition-colors {activeSymbols.has(
							symbol.name
						)
							? 'border-slate-900 bg-slate-900 text-white dark:border-white dark:bg-white dark:text-slate-900'
							: 'border-slate-300 text-slate-600 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800'}"
					>
						{symbol.name}
					</button>
				{/each}
			</div>
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
			onclick={save}
			disabled={saving}
			class="w-fit rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
		>
			{saving ? 'Saving…' : 'Save Settings'}
		</button>
	{/if}
</div>
