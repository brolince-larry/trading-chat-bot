<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { Direction, PositionOut, PriceOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { formatMoney, formatPrice, pnlColor } from '$lib/format';

	let { symbol }: { symbol: string } = $props();

	let price = $state<PriceOut | null>(null);
	let openPosition = $state<PositionOut | null>(null);
	let message = $state<string | null>(null);
	let messageIsError = $state(false);
	let busy = $state(false);

	// Manual entry form.
	let direction = $state<Direction>('long');
	let entryPrice = $state('');
	let stopLoss = $state('');
	let takeProfit = $state('');
	let accountBalance = $state('10000');
	let riskPercent = $state('1');

	// Editing an open position's stops.
	let editStopLoss = $state('');
	let editTakeProfit = $state('');

	function setMessage(text: string, isError = false) {
		message = text;
		messageIsError = isError;
	}

	async function refreshPosition() {
		try {
			const open = await api.listPositions('open');
			openPosition = open.find((p) => p.symbol === symbol) ?? null;
			if (openPosition) {
				editStopLoss = openPosition.stop_loss;
				editTakeProfit = openPosition.take_profit ?? '';
			}
		} catch {
			// Live WS updates will retry shortly; a one-off failure here isn't fatal.
		}
	}

	async function loadPrice() {
		try {
			price = await api.getPrice(symbol);
			if (!entryPrice) entryPrice = direction === 'long' ? price.ask : price.bid;
		} catch {
			// Handled by the live prices socket / chart already showing an error.
		}
	}

	async function enterTrade() {
		if (!entryPrice || !stopLoss) {
			setMessage('Entry price and stop-loss are required.', true);
			return;
		}
		busy = true;
		message = null;
		try {
			const sizing = await api.calculatePositionSize({
				symbol,
				account_balance: accountBalance,
				risk_percent: riskPercent,
				entry_price: entryPrice,
				stop_loss_price: stopLoss,
				account_currency: 'USD'
			});
			if (sizing.lots === '0' || !sizing.meets_minimum_lot) {
				setMessage('Calculated position size is below the broker minimum lot.', true);
				return;
			}
			await api.openPosition({
				symbol,
				strategy: 'manual',
				direction,
				entry_price: entryPrice,
				stop_loss: stopLoss,
				take_profit: takeProfit || null,
				lots: sizing.lots,
				units: sizing.units,
				account_currency: 'USD',
				pip_value_per_unit: sizing.pip_value_per_unit
			});
			setMessage(`Opened a ${sizing.lots}-lot ${direction} position on ${symbol}.`);
			await refreshPosition();
		} catch (err) {
			setMessage(err instanceof ApiError ? err.message : 'Could not open the trade.', true);
		} finally {
			busy = false;
		}
	}

	async function updateStops() {
		if (!openPosition) return;
		busy = true;
		message = null;
		try {
			openPosition = await api.updatePositionStops(openPosition.id, {
				stop_loss: editStopLoss || null,
				take_profit: editTakeProfit || null
			});
			setMessage('Stop-loss / take-profit updated.');
		} catch (err) {
			setMessage(err instanceof ApiError ? err.message : 'Could not update stops.', true);
		} finally {
			busy = false;
		}
	}

	async function exitTrade(reasonLabel: string) {
		if (!openPosition) return;
		busy = true;
		message = null;
		try {
			const closed = await api.closePosition(openPosition.id);
			setMessage(
				`${reasonLabel}: closed at ${formatPrice(closed.close_price)} (P&L ${formatMoney(closed.realized_pnl)}).`
			);
			openPosition = null;
		} catch (err) {
			setMessage(err instanceof ApiError ? err.message : 'Could not close the position.', true);
		} finally {
			busy = false;
		}
	}

	let stopLiveTicks: (() => void) | null = null;
	let stopLivePositions: (() => void) | null = null;

	onMount(() => {
		refreshPosition();
		loadPrice();
		stopLiveTicks = connectLiveSocket<Record<string, PriceOut>>('/ws/prices', (prices) => {
			const tick = prices[symbol];
			if (tick) price = tick;
		});
		stopLivePositions = connectLiveSocket<PositionOut[]>('/ws/positions', (positions) => {
			const match = positions.find((p) => p.symbol === symbol);
			openPosition = match ?? null;
		});
		return () => {
			stopLiveTicks?.();
			stopLivePositions?.();
		};
	});
</script>

<div class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
	<h2 class="text-sm font-semibold">Trade — {symbol}</h2>

	{#if message}
		<div
			class="mt-2 rounded border px-3 py-2 text-xs {messageIsError
				? 'border-rose-300 bg-rose-50 text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300'
				: 'border-sky-300 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950/40 dark:text-sky-300'}"
		>
			{message}
		</div>
	{/if}

	{#if openPosition}
		<div class="mt-3 flex flex-col gap-3">
			<div class="flex items-center justify-between text-sm">
				<span class="font-medium capitalize">{openPosition.direction} {openPosition.lots} lots</span
				>
				<span class={pnlColor(openPosition.unrealized_pnl)}
					>{formatMoney(openPosition.unrealized_pnl)}</span
				>
			</div>
			<p class="text-xs text-slate-400">Entry {formatPrice(openPosition.entry_price)}</p>

			<div class="grid grid-cols-2 gap-2">
				<label class="flex flex-col gap-1 text-xs text-slate-500">
					Stop-loss
					<input
						type="text"
						bind:value={editStopLoss}
						class="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
					/>
				</label>
				<label class="flex flex-col gap-1 text-xs text-slate-500">
					Take-profit
					<input
						type="text"
						bind:value={editTakeProfit}
						class="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
					/>
				</label>
			</div>
			<button
				onclick={updateStops}
				disabled={busy}
				class="rounded border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:hover:bg-slate-800"
			>
				Update stop / target
			</button>

			<div class="mt-1 grid grid-cols-2 gap-2">
				<button
					onclick={() => exitTrade('Exit Trade')}
					disabled={busy}
					class="rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
				>
					Exit Trade
				</button>
				<button
					onclick={() => exitTrade('🔥 Fire')}
					disabled={busy}
					class="rounded bg-rose-600 px-3 py-2 text-sm font-bold text-white hover:bg-rose-700 disabled:opacity-50"
				>
					🔥 Fire — Exit Now
				</button>
			</div>
			<p class="text-xs text-slate-400">
				Fire immediately exits at the current market price — use it the moment the market reverses
				against this position.
			</p>
		</div>
	{:else}
		<div class="mt-3 flex flex-col gap-3">
			<div class="flex gap-2">
				<button
					onclick={() => (direction = 'long')}
					class="flex-1 rounded px-3 py-1.5 text-sm font-medium {direction === 'long'
						? 'bg-emerald-600 text-white'
						: 'border border-slate-300 dark:border-slate-700'}"
				>
					Long
				</button>
				<button
					onclick={() => (direction = 'short')}
					class="flex-1 rounded px-3 py-1.5 text-sm font-medium {direction === 'short'
						? 'bg-rose-600 text-white'
						: 'border border-slate-300 dark:border-slate-700'}"
				>
					Short
				</button>
			</div>

			{#if price}
				<p class="text-xs text-slate-400">
					Bid {formatPrice(price.bid)} · Ask {formatPrice(price.ask)}
				</p>
			{/if}

			<div class="grid grid-cols-2 gap-2">
				<label class="flex flex-col gap-1 text-xs text-slate-500">
					Entry
					<input
						type="text"
						bind:value={entryPrice}
						class="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
					/>
				</label>
				<label class="flex flex-col gap-1 text-xs text-slate-500">
					Stop-loss
					<input
						type="text"
						bind:value={stopLoss}
						class="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
					/>
				</label>
				<label class="flex flex-col gap-1 text-xs text-slate-500">
					Take-profit (optional)
					<input
						type="text"
						bind:value={takeProfit}
						class="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
					/>
				</label>
				<label class="flex flex-col gap-1 text-xs text-slate-500">
					Risk %
					<input
						type="text"
						bind:value={riskPercent}
						class="rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
					/>
				</label>
			</div>

			<button
				onclick={enterTrade}
				disabled={busy}
				class="rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{busy ? 'Opening…' : 'Enter Trade'}
			</button>
		</div>
	{/if}
</div>
