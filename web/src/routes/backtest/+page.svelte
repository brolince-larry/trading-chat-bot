<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { BacktestResultOut, SymbolOut } from '$lib/api/types';
	import EquityChart from '$lib/components/EquityChart.svelte';
	import { formatMoney, formatPrice, pnlColor } from '$lib/format';

	const strategies = [
		{ value: 'trend_pullback', label: 'Trend Pullback' },
		{ value: 'breakout_retest', label: 'Breakout Retest' },
		{ value: 'range_reversion', label: 'Range Reversion' }
	];

	const timeframes = [
		{ value: '15m', label: '15m' },
		{ value: '30m', label: '30m' },
		{ value: '1h', label: '1h' },
		{ value: '4h', label: '4h' },
		{ value: '1d', label: '1d' }
	];

	let symbols = $state<SymbolOut[]>([]);
	let symbol = $state('EUR_USD');
	let strategy = $state('trend_pullback');
	let higherTimeframe = $state('4h');
	let entryTimeframe = $state('1h');
	let lookbackCandles = $state('500');
	let startingBalance = $state('10000');
	let riskPercent = $state('1');
	let accountCurrency = $state('USD');
	let quoteToAccountRate = $state('');

	let result = $state<BacktestResultOut | null>(null);
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
			result = await api.runBacktest({
				symbol,
				strategy,
				higher_timeframe: higherTimeframe,
				entry_timeframe: entryTimeframe,
				lookback_candles: Number(lookbackCandles),
				starting_balance: startingBalance,
				risk_percent: riskPercent,
				account_currency: accountCurrency,
				quote_to_account_rate: quoteToAccountRate || null
			});
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not run the backtest.';
		} finally {
			loading = false;
		}
	}

	const exitReasonLabel = {
		stop_loss: 'Stop Loss',
		take_profit: 'Take Profit',
		end_of_data: 'End of Data'
	} as const;
</script>

<svelte:head><title>Backtest — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="text-xl font-semibold">Strategy Backtest</h1>
		<p class="mt-1 text-sm text-slate-500">
			Runs the exact same strategy and position-sizing logic used in live trading against historical
			candles — no separate simulation logic.
		</p>
	</div>

	<form
		onsubmit={submit}
		class="grid grid-cols-2 gap-4 rounded border border-slate-200 bg-white p-4 sm:grid-cols-3 md:grid-cols-4 dark:border-slate-800 dark:bg-slate-900"
	>
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

		<label class="flex flex-col gap-1 text-sm">
			Strategy
			<select
				bind:value={strategy}
				class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
			>
				{#each strategies as s (s.value)}
					<option value={s.value}>{s.label}</option>
				{/each}
			</select>
		</label>

		<label class="flex flex-col gap-1 text-sm">
			Higher timeframe
			<select
				bind:value={higherTimeframe}
				class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
			>
				{#each timeframes as t (t.value)}
					<option value={t.value}>{t.label}</option>
				{/each}
			</select>
		</label>

		<label class="flex flex-col gap-1 text-sm">
			Entry timeframe
			<select
				bind:value={entryTimeframe}
				class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
			>
				{#each timeframes as t (t.value)}
					<option value={t.value}>{t.label}</option>
				{/each}
			</select>
		</label>

		<label class="flex flex-col gap-1 text-sm">
			Lookback candles
			<input
				type="number"
				step="1"
				min="70"
				max="3000"
				required
				bind:value={lookbackCandles}
				class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
			/>
		</label>

		<label class="flex flex-col gap-1 text-sm">
			Starting balance
			<input
				type="number"
				step="any"
				required
				bind:value={startingBalance}
				class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
			/>
		</label>

		<label class="flex flex-col gap-1 text-sm">
			Risk % per trade
			<input
				type="number"
				step="any"
				required
				bind:value={riskPercent}
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

		<label class="col-span-2 flex flex-col gap-1 text-sm sm:col-span-3 md:col-span-4">
			Quote→account conversion rate (optional — only needed if the pair's quote currency differs
			from your account currency)
			<input
				type="number"
				step="any"
				bind:value={quoteToAccountRate}
				class="rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
			/>
		</label>

		<div class="col-span-2 sm:col-span-3 md:col-span-4">
			<button
				type="submit"
				disabled={loading}
				class="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{loading ? 'Running…' : 'Run Backtest'}
			</button>
		</div>
	</form>

	{#if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{:else if result}
		<div class="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
			<div
				class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="text-xs text-slate-400">Total return</div>
				<div
					class="text-lg font-semibold tabular-nums {result.total_return_percent >= 0
						? 'text-emerald-600 dark:text-emerald-400'
						: 'text-rose-600 dark:text-rose-400'}"
				>
					{result.total_return_percent.toFixed(2)}%
				</div>
			</div>
			<div
				class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="text-xs text-slate-400">Trades</div>
				<div class="text-lg font-semibold tabular-nums">{result.total_trades}</div>
			</div>
			<div
				class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="text-xs text-slate-400">Win rate</div>
				<div class="text-lg font-semibold tabular-nums">
					{result.win_rate !== null ? `${(result.win_rate * 100).toFixed(1)}%` : '—'}
				</div>
			</div>
			<div
				class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="text-xs text-slate-400">Profit factor</div>
				<div class="text-lg font-semibold tabular-nums">
					{result.profit_factor !== null ? result.profit_factor.toFixed(2) : '—'}
				</div>
			</div>
			<div
				class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="text-xs text-slate-400">Expectancy (R)</div>
				<div class="text-lg font-semibold tabular-nums">
					{result.expectancy_r !== null ? result.expectancy_r.toFixed(2) : '—'}
				</div>
			</div>
			<div
				class="rounded border border-slate-200 bg-white p-3 dark:border-slate-800 dark:bg-slate-900"
			>
				<div class="text-xs text-slate-400">Max drawdown</div>
				<div class="text-lg font-semibold text-rose-600 tabular-nums dark:text-rose-400">
					{result.max_drawdown_percent.toFixed(2)}%
				</div>
			</div>
		</div>

		<div
			class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="mb-3 text-sm font-medium text-slate-500">Equity Curve</h2>
			{#if result.equity_curve.length > 0}
				<EquityChart points={result.equity_curve} />
			{:else}
				<p class="text-sm text-slate-500">No trades were taken over this period.</p>
			{/if}
		</div>

		<div
			class="overflow-x-auto rounded border border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
		>
			<h2 class="p-4 pb-0 text-sm font-medium text-slate-500">Trade Log</h2>
			{#if result.trades.length === 0}
				<p class="p-4 text-sm text-slate-500">No trades were taken over this period.</p>
			{:else}
				<table class="w-full min-w-[720px] text-sm">
					<thead>
						<tr
							class="border-b border-slate-200 text-left text-xs text-slate-400 dark:border-slate-800"
						>
							<th class="px-4 py-2 font-medium">Direction</th>
							<th class="px-4 py-2 font-medium">Entry</th>
							<th class="px-4 py-2 font-medium">Exit</th>
							<th class="px-4 py-2 font-medium">Reason</th>
							<th class="px-4 py-2 font-medium">Bars</th>
							<th class="px-4 py-2 font-medium">R</th>
							<th class="px-4 py-2 font-medium">P&L</th>
						</tr>
					</thead>
					<tbody>
						{#each result.trades as trade, i (i)}
							<tr class="border-b border-slate-100 last:border-0 dark:border-slate-800/60">
								<td class="px-4 py-2 capitalize">{trade.direction}</td>
								<td class="px-4 py-2 tabular-nums">{formatPrice(trade.entry_price)}</td>
								<td class="px-4 py-2 tabular-nums">{formatPrice(trade.exit_price)}</td>
								<td class="px-4 py-2">{exitReasonLabel[trade.exit_reason]}</td>
								<td class="px-4 py-2 tabular-nums">{trade.bars_held}</td>
								<td class="px-4 py-2 tabular-nums">{Number(trade.r_multiple).toFixed(2)}</td>
								<td class="px-4 py-2 tabular-nums {pnlColor(trade.pnl)}">
									{formatMoney(trade.pnl)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			{/if}
		</div>
	{:else}
		<p class="text-sm text-slate-500">Configure a run above and click "Run Backtest".</p>
	{/if}
</div>
