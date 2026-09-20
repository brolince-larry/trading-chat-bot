<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { PositionSizeResponseOut, SymbolOut } from '$lib/api/types';

	let symbols = $state<SymbolOut[]>([]);
	let symbol = $state('EUR_USD');
	let accountBalance = $state('10000');
	let riskPercent = $state('1');
	let entryPrice = $state('');
	let stopLossPrice = $state('');
	let accountCurrency = $state('USD');
	let quoteToAccountRate = $state('');

	let result = $state<PositionSizeResponseOut | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			symbols = await api.getSymbols();
		} catch {
			// Symbol list is a convenience for the dropdown; the form still works without it.
		}
	});

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		loading = true;
		error = null;
		result = null;
		try {
			result = await api.calculatePositionSize({
				symbol,
				account_balance: accountBalance,
				risk_percent: riskPercent,
				entry_price: entryPrice,
				stop_loss_price: stopLossPrice,
				account_currency: accountCurrency,
				quote_to_account_rate: quoteToAccountRate || null
			});
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not calculate position size.';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head><title>Position Size — Forex AI Market Scanner</title></svelte:head>

<div class="grid gap-6 md:grid-cols-2">
	<div>
		<h1 class="mb-4 text-xl font-semibold">Position Size Calculator</h1>
		<form onsubmit={submit} class="flex flex-col gap-4">
			<label class="flex flex-col gap-1 text-sm">
				Symbol
				<select
					bind:value={symbol}
					class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
				>
					{#if symbols.length === 0}
						<option value="EUR_USD">EUR_USD</option>
					{/if}
					{#each symbols as s (s.name)}
						<option value={s.name}>{s.name}</option>
					{/each}
				</select>
			</label>

			<div class="grid grid-cols-2 gap-4">
				<label class="flex flex-col gap-1 text-sm">
					Account balance
					<input
						type="number"
						step="any"
						required
						bind:value={accountBalance}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
				<label class="flex flex-col gap-1 text-sm">
					Account currency
					<input
						maxlength="3"
						required
						bind:value={accountCurrency}
						class="rounded border border-slate-300 bg-white px-3 py-2 uppercase dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
			</div>

			<label class="flex flex-col gap-1 text-sm">
				Risk percent (of account balance)
				<input
					type="number"
					step="any"
					required
					bind:value={riskPercent}
					class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
				/>
			</label>

			<div class="grid grid-cols-2 gap-4">
				<label class="flex flex-col gap-1 text-sm">
					Entry price
					<input
						type="number"
						step="any"
						required
						bind:value={entryPrice}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
				<label class="flex flex-col gap-1 text-sm">
					Stop-loss price
					<input
						type="number"
						step="any"
						required
						bind:value={stopLossPrice}
						class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
					/>
				</label>
			</div>

			<label class="flex flex-col gap-1 text-sm">
				Quote→account conversion rate (optional — only needed if the pair's quote currency differs
				from your account currency)
				<input
					type="number"
					step="any"
					bind:value={quoteToAccountRate}
					class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
				/>
			</label>

			<button
				type="submit"
				disabled={loading}
				class="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{loading ? 'Calculating…' : 'Calculate'}
			</button>
		</form>
	</div>

	<div>
		<h2 class="mb-4 text-xl font-semibold">Result</h2>

		{#if error}
			<div
				class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
			>
				{error}
			</div>
		{:else if result}
			<dl
				class="grid grid-cols-2 gap-x-4 gap-y-3 rounded border border-slate-200 bg-white p-4 text-sm dark:border-slate-800 dark:bg-slate-900"
			>
				<div>
					<dt class="text-slate-400">Risk amount</dt>
					<dd class="tabular-nums">{result.risk_amount} {result.account_currency}</dd>
				</div>
				<div>
					<dt class="text-slate-400">Stop distance</dt>
					<dd class="tabular-nums">{result.stop_distance_pips} pips</dd>
				</div>
				<div>
					<dt class="text-slate-400">Pip value / unit</dt>
					<dd class="tabular-nums">{result.pip_value_per_unit}</dd>
				</div>
				<div>
					<dt class="text-slate-400">Position size</dt>
					<dd class="font-semibold tabular-nums">{result.lots} lots ({result.units} units)</dd>
				</div>
				<div class="col-span-2">
					<dt class="text-slate-400">Meets broker minimum lot</dt>
					<dd>{result.meets_minimum_lot ? 'Yes' : 'No'}</dd>
				</div>
			</dl>
			{#if result.warnings.length > 0}
				<ul class="mt-3 list-disc space-y-1 pl-5 text-sm text-amber-700 dark:text-amber-400">
					{#each result.warnings as warning (warning)}
						<li>{warning}</li>
					{/each}
				</ul>
			{/if}
		{:else}
			<p class="text-sm text-slate-500">Fill out the form to calculate a position size.</p>
		{/if}
	</div>
</div>
