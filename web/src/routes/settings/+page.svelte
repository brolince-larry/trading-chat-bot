<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { HealthOut } from '$lib/api/types';

	const DISPLAY_NAME_KEY = 'display_name';

	let health = $state<HealthOut | null>(null);
	let healthError = $state<string | null>(null);

	let displayName = $state('');
	let nameSaved = $state(false);

	let startingBalance = $state('10000');
	let balanceSaving = $state(false);
	let balanceSaved = $state(false);
	let balanceError = $state<string | null>(null);

	let notifyTradeClosed = $state(true);
	let notifyNewSignal = $state(true);
	let notifyRiskAlert = $state(true);
	let notifyBotUpdate = $state(false);

	const NOTIFY_PREFS_KEY = 'notification_prefs';

	onMount(async () => {
		try {
			displayName = localStorage.getItem(DISPLAY_NAME_KEY) ?? '';
			const storedPrefs = localStorage.getItem(NOTIFY_PREFS_KEY);
			if (storedPrefs) {
				const prefs = JSON.parse(storedPrefs);
				notifyTradeClosed = prefs.tradeClosed ?? true;
				notifyNewSignal = prefs.newSignal ?? true;
				notifyRiskAlert = prefs.riskAlert ?? true;
				notifyBotUpdate = prefs.botUpdate ?? false;
			}
		} catch {
			// Local-only preferences; a blocked/unavailable storage just keeps defaults.
		}

		try {
			health = await api.getHealth();
		} catch (err) {
			healthError = err instanceof ApiError ? err.message : 'Could not reach the API server.';
		}

		try {
			const settings = await api.getAccountSettings();
			startingBalance = settings.starting_balance;
		} catch {
			// Falls back to the form's default; the account API may be briefly unavailable.
		}
	});

	function saveDisplayName() {
		try {
			localStorage.setItem(DISPLAY_NAME_KEY, displayName);
			nameSaved = true;
			setTimeout(() => (nameSaved = false), 2000);
		} catch {
			// Storage unavailable — nothing to persist, silently no-op.
		}
	}

	function saveNotificationPrefs() {
		try {
			localStorage.setItem(
				NOTIFY_PREFS_KEY,
				JSON.stringify({
					tradeClosed: notifyTradeClosed,
					newSignal: notifyNewSignal,
					riskAlert: notifyRiskAlert,
					botUpdate: notifyBotUpdate
				})
			);
		} catch {
			// Storage unavailable — preference just won't persist across reloads.
		}
	}

	async function saveStartingBalance(event: SubmitEvent) {
		event.preventDefault();
		balanceSaving = true;
		balanceError = null;
		balanceSaved = false;
		try {
			await api.updateAccountSettings({ starting_balance: startingBalance });
			balanceSaved = true;
		} catch (err) {
			balanceError = err instanceof ApiError ? err.message : 'Could not save starting balance.';
		} finally {
			balanceSaving = false;
		}
	}
</script>

<svelte:head><title>Settings — Forex AI Market Scanner</title></svelte:head>

<div class="flex max-w-2xl flex-col gap-6">
	<div>
		<h1 class="mb-1 text-xl font-semibold">Settings &amp; Account</h1>
		<p class="text-sm text-slate-500">
			This is a self-hosted paper-trading tool — there's no account system or billing. Settings
			below are local to this browser except the starting balance, which is stored server-side.
		</p>
	</div>

	<section
		class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
	>
		<h2 class="mb-3 text-sm font-semibold">Profile</h2>
		<label class="flex flex-col gap-1 text-sm">
			Display name (shown only in this browser — not sent anywhere)
			<div class="flex gap-2">
				<input
					type="text"
					bind:value={displayName}
					placeholder="e.g. Trader"
					class="flex-1 rounded border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-950"
				/>
				<button
					onclick={saveDisplayName}
					class="rounded border border-slate-300 px-3 py-2 text-sm font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
				>
					Save
				</button>
			</div>
		</label>
		{#if nameSaved}
			<p class="mt-2 text-xs text-emerald-600 dark:text-emerald-400">Saved.</p>
		{/if}
	</section>

	<section
		class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
	>
		<h2 class="mb-1 text-sm font-semibold">Market Data Provider</h2>
		{#if healthError}
			<p class="text-xs text-rose-600 dark:text-rose-400">{healthError}</p>
		{:else if health}
			<div class="flex items-center gap-2 text-sm">
				<span class="h-2 w-2 rounded-full bg-emerald-500"></span>
				<span class="font-medium capitalize">{health.market_data_provider}</span>
				<span class="text-slate-400">
					{health.market_data_provider === 'simulated'
						? '— deterministic synthetic prices, no credentials needed'
						: '— live OANDA v20 REST feed'}
				</span>
			</div>
			<p class="mt-1 text-xs text-slate-400">
				No broker account is linked for order execution — every trade here is a simulated paper
				position. Set <code>MARKET_DATA_PROVIDER=oanda</code> and <code>OANDA_API_KEY</code> in the backend
				environment to switch to live OANDA prices.
			</p>
		{:else}
			<p class="text-xs text-slate-400">Loading…</p>
		{/if}
	</section>

	<section
		class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
	>
		<h2 class="mb-1 text-sm font-semibold">Paper Account Balance</h2>
		<p class="mb-3 text-xs text-slate-400">
			The balance the Dashboard's equity curve starts from — not a real deposit.
		</p>
		<form onsubmit={saveStartingBalance} class="flex gap-2">
			<input
				type="number"
				step="any"
				min="1"
				bind:value={startingBalance}
				class="max-w-xs flex-1 rounded border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-950"
			/>
			<button
				type="submit"
				disabled={balanceSaving}
				class="rounded bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50 dark:bg-white dark:text-slate-900"
			>
				{balanceSaving ? 'Saving…' : 'Save'}
			</button>
		</form>
		{#if balanceError}
			<p class="mt-2 text-xs text-rose-600 dark:text-rose-400">{balanceError}</p>
		{/if}
		{#if balanceSaved}
			<p class="mt-2 text-xs text-emerald-600 dark:text-emerald-400">Saved.</p>
		{/if}
	</section>

	<section
		class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
	>
		<h2 class="mb-3 text-sm font-semibold">Notification Preferences</h2>
		<p class="mb-3 text-xs text-slate-400">
			Stored in this browser only — the bell always receives every event; this just controls which
			ones you'd want surfaced if browser push is added later.
		</p>
		<div class="flex flex-col gap-2 text-sm">
			<label class="flex items-center gap-2">
				<input type="checkbox" bind:checked={notifyTradeClosed} onchange={saveNotificationPrefs} />
				Trade closed
			</label>
			<label class="flex items-center gap-2">
				<input type="checkbox" bind:checked={notifyNewSignal} onchange={saveNotificationPrefs} />
				New signal confirmed
			</label>
			<label class="flex items-center gap-2">
				<input type="checkbox" bind:checked={notifyRiskAlert} onchange={saveNotificationPrefs} />
				Risk alerts
			</label>
			<label class="flex items-center gap-2">
				<input type="checkbox" bind:checked={notifyBotUpdate} onchange={saveNotificationPrefs} />
				Bot started/paused
			</label>
		</div>
	</section>

	<section
		class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
	>
		<h2 class="mb-1 text-sm font-semibold">About</h2>
		<p class="text-xs text-slate-400">
			{health?.app_name ?? 'Forex AI Market Scanner'} — environment: {health?.environment ?? '—'}.
			No subscription or billing exists in this build.
		</p>
	</section>
</div>
