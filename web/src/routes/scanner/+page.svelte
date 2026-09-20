<script lang="ts">
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { api, ApiError } from '$lib/api/client';
	import type { ScannedCandidateOut, ScanResultOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import {
		directionColor,
		exposureColor,
		formatDateTime,
		formatPrice,
		statusColor
	} from '$lib/format';

	let result = $state<ScanResultOut | null>(null);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let minScore = $state(0);
	let live = $state(false);
	let openingSymbol = $state<string | null>(null);
	let openMessage = $state<string | null>(null);

	const filteredCandidates = $derived(
		result ? result.candidates.filter((c) => c.quality_score >= minScore) : []
	);

	async function runScan() {
		loading = true;
		error = null;
		try {
			result = await api.runScan();
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Something went wrong running the scan.';
		} finally {
			loading = false;
		}
	}

	async function openFromCandidate(candidate: ScannedCandidateOut) {
		const setup = candidate.setup;
		if (setup.entry_price == null || setup.stop_loss == null) return;

		openingSymbol = setup.symbol;
		openMessage = null;
		try {
			const sizing = await api.calculatePositionSize({
				symbol: setup.symbol,
				account_balance: '10000',
				risk_percent: '1',
				entry_price: String(setup.entry_price),
				stop_loss_price: String(setup.stop_loss),
				account_currency: 'USD'
			});
			if (sizing.lots === '0' || !sizing.meets_minimum_lot) {
				openMessage = `${setup.symbol}: calculated size is below the broker minimum lot.`;
				return;
			}
			await api.openPosition({
				symbol: setup.symbol,
				strategy: setup.strategy,
				direction: setup.direction,
				entry_price: String(setup.entry_price),
				stop_loss: String(setup.stop_loss),
				take_profit: setup.take_profits[0] ? String(setup.take_profits[0].price) : null,
				lots: sizing.lots,
				units: sizing.units,
				account_currency: 'USD',
				pip_value_per_unit: sizing.pip_value_per_unit
			});
			openMessage = `Opened a ${sizing.lots}-lot ${setup.direction} paper position on ${setup.symbol}.`;
		} catch (err) {
			openMessage =
				err instanceof ApiError
					? `${setup.symbol}: ${err.message}`
					: `${setup.symbol}: could not open the position.`;
		} finally {
			openingSymbol = null;
		}
	}

	onMount(() => {
		runScan();
		return connectLiveSocket<ScanResultOut>(
			'/ws/scanner',
			(data) => {
				result = data;
			},
			{
				onOpen: () => (live = true),
				onClose: () => (live = false)
			}
		);
	});
</script>

<svelte:head><title>Scanner — Forex AI Market Scanner</title></svelte:head>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-center justify-between gap-4">
		<div>
			<div class="flex items-center gap-2">
				<h1 class="text-xl font-semibold">Pair Scanner</h1>
				<span class="flex items-center gap-1.5 text-xs text-slate-500">
					<span
						class="h-2 w-2 rounded-full {live
							? 'bg-emerald-500'
							: 'bg-slate-300 dark:bg-slate-700'}"
					></span>
					{live ? 'Live' : 'Connecting…'}
				</span>
			</div>
			{#if result}
				<p class="text-sm text-slate-500">
					Scanned {result.symbols_scanned} pairs at {formatDateTime(result.scanned_at)}
				</p>
			{/if}
		</div>
		<div class="flex items-center gap-3">
			<label class="flex items-center gap-2 text-sm text-slate-500">
				Min score
				<input
					type="number"
					min="0"
					max="100"
					bind:value={minScore}
					class="w-16 rounded border border-slate-300 bg-white px-2 py-1 text-slate-900 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100"
				/>
			</label>
			<button
				onclick={runScan}
				disabled={loading}
				class="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{loading ? 'Scanning…' : 'Rescan Now'}
			</button>
		</div>
	</div>

	{#if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{/if}

	{#if openMessage}
		<div
			class="rounded border border-sky-300 bg-sky-50 px-4 py-3 text-sm text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-300"
		>
			{openMessage}
		</div>
	{/if}

	{#if result}
		{#if result.currency_exposure.length > 0}
			<div class="flex flex-wrap items-center gap-2">
				<span class="text-sm text-slate-500">Currency exposure:</span>
				{#each result.currency_exposure as exposure (exposure.currency)}
					<span
						class="rounded-full px-2.5 py-1 text-xs font-medium {exposureColor(exposure.level)}"
					>
						{exposure.currency}
						{exposure.net_position_count > 0 ? '+' : ''}{exposure.net_position_count}
					</span>
				{/each}
			</div>
		{/if}

		{#if filteredCandidates.length === 0}
			<p
				class="rounded border border-slate-200 bg-white px-4 py-6 text-center text-sm text-slate-500 dark:border-slate-800 dark:bg-slate-900"
			>
				No actionable setups right now. That's a normal, expected outcome — not every scan should
				produce a trade.
			</p>
		{:else}
			<div class="overflow-x-auto rounded border border-slate-200 dark:border-slate-800">
				<table class="w-full min-w-[980px] text-sm">
					<thead class="bg-slate-100 text-left text-xs text-slate-500 uppercase dark:bg-slate-900">
						<tr>
							<th class="px-3 py-2">Pair</th>
							<th class="px-3 py-2">Strategy</th>
							<th class="px-3 py-2">Direction</th>
							<th class="px-3 py-2">Status</th>
							<th class="px-3 py-2">Score</th>
							<th class="px-3 py-2">Entry</th>
							<th class="px-3 py-2">Stop</th>
							<th class="px-3 py-2">Take Profit</th>
							<th class="px-3 py-2">R:R</th>
							<th class="px-3 py-2"></th>
						</tr>
					</thead>
					<tbody class="divide-y divide-slate-200 dark:divide-slate-800">
						{#each filteredCandidates as candidate (candidate.setup.symbol + candidate.setup.strategy)}
							<tr class="hover:bg-slate-50 dark:hover:bg-slate-900/60">
								<td class="px-3 py-2 font-medium">
									<a
										href={resolve('/analysis/[symbol]', { symbol: candidate.setup.symbol })}
										class="hover:underline"
									>
										{candidate.setup.symbol}
									</a>
								</td>
								<td class="px-3 py-2 text-slate-500"
									>{candidate.setup.strategy.replace('_', ' ')}</td
								>
								<td
									class="px-3 py-2 font-medium capitalize {directionColor(
										candidate.setup.direction
									)}"
								>
									{candidate.setup.direction}
								</td>
								<td class="px-3 py-2">
									<span
										class="rounded-full px-2.5 py-1 text-xs font-medium {statusColor(
											candidate.setup.status
										)}"
									>
										{candidate.setup.status}
									</span>
								</td>
								<td class="px-3 py-2 font-medium">{candidate.quality_score}</td>
								<td class="px-3 py-2 tabular-nums">{formatPrice(candidate.setup.entry_price)}</td>
								<td class="px-3 py-2 tabular-nums">{formatPrice(candidate.setup.stop_loss)}</td>
								<td class="px-3 py-2 tabular-nums">
									{candidate.setup.take_profits.map((tp) => formatPrice(tp.price)).join(' / ') ||
										'—'}
								</td>
								<td class="px-3 py-2 tabular-nums">
									{candidate.setup.risk_reward ? candidate.setup.risk_reward.toFixed(2) : '—'}
								</td>
								<td class="px-3 py-2">
									{#if candidate.setup.status === 'confirmed'}
										<button
											onclick={() => openFromCandidate(candidate)}
											disabled={openingSymbol === candidate.setup.symbol}
											class="rounded border border-slate-300 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
										>
											{openingSymbol === candidate.setup.symbol ? 'Opening…' : 'Open'}
										</button>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}

		{#if result.skipped.length > 0}
			<p class="text-xs text-slate-400">
				Skipped: {result.skipped.map((s) => `${s.symbol} (${s.reason})`).join(', ')}
			</p>
		{/if}
	{/if}
</div>
