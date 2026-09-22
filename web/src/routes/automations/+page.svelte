<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let saved = $state(false);

	let breakevenEnabled = $state(false);
	let breakevenAtR = $state('1.0');
	let trailingStopEnabled = $state(false);
	let trailingStopPips = $state('20');

	onMount(async () => {
		try {
			const settings = await api.getAutomationSettings();
			breakevenEnabled = settings.breakeven_enabled;
			breakevenAtR = settings.breakeven_at_r;
			trailingStopEnabled = settings.trailing_stop_enabled;
			trailingStopPips = settings.trailing_stop_pips;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load automation settings.';
		} finally {
			loading = false;
		}
	});

	async function save() {
		saving = true;
		error = null;
		saved = false;
		try {
			await api.updateAutomationSettings({
				breakeven_enabled: breakevenEnabled,
				breakeven_at_r: breakevenAtR,
				trailing_stop_enabled: trailingStopEnabled,
				trailing_stop_pips: trailingStopPips
			});
			saved = true;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not save automation settings.';
		} finally {
			saving = false;
		}
	}
</script>

<svelte:head><title>Automations — Forex AI Market Scanner</title></svelte:head>

<div class="flex max-w-xl flex-col gap-6">
	<div>
		<h1 class="text-xl font-semibold">Automations</h1>
		<p class="text-sm text-slate-500">
			Rules the background loop applies to positions you've already opened — it only ever tightens a
			stop-loss, never opens or closes a trade on its own.
		</p>
	</div>

	{#if loading}
		<p class="text-sm text-slate-500">Loading…</p>
	{:else}
		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<label class="flex items-center justify-between">
				<span>
					<span class="text-sm font-medium">Breakeven Protection</span>
					<p class="text-xs text-slate-400">
						Move the stop-loss to entry once a trade reaches a set R-multiple.
					</p>
				</span>
				<input type="checkbox" bind:checked={breakevenEnabled} class="h-5 w-5" />
			</label>
			{#if breakevenEnabled}
				<label class="mt-3 flex items-center gap-2 text-sm">
					Move to breakeven after
					<input
						type="number"
						step="0.1"
						min="0.1"
						bind:value={breakevenAtR}
						class="w-20 rounded border border-slate-300 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-950"
					/>
					R profit
				</label>
			{/if}
		</div>

		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<label class="flex items-center justify-between">
				<span>
					<span class="text-sm font-medium">Trailing Stop</span>
					<p class="text-xs text-slate-400">
						Trail the stop-loss a fixed distance behind the current price.
					</p>
				</span>
				<input type="checkbox" bind:checked={trailingStopEnabled} class="h-5 w-5" />
			</label>
			{#if trailingStopEnabled}
				<label class="mt-3 flex items-center gap-2 text-sm">
					Trail by
					<input
						type="number"
						step="1"
						min="1"
						bind:value={trailingStopPips}
						class="w-20 rounded border border-slate-300 bg-white px-2 py-1 dark:border-slate-700 dark:bg-slate-950"
					/>
					pips
				</label>
			{/if}
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
