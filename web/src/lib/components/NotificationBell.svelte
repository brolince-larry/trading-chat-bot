<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { NotificationOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { formatDateTime } from '$lib/format';
	import Icon from '$lib/components/Icon.svelte';

	let notifications = $state<NotificationOut[]>([]);
	let open = $state(false);
	let error = $state<string | null>(null);

	const unreadCount = $derived(notifications.filter((n) => !n.read).length);

	const TYPE_LABEL: Record<string, string> = {
		trade_closed: 'Trade closed',
		new_signal: 'New signal',
		risk_alert: 'Risk alert',
		bot_update: 'Bot update'
	};

	const TYPE_COLOR: Record<string, string> = {
		trade_closed: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
		new_signal: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
		risk_alert: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300',
		bot_update: 'bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300'
	};

	async function load() {
		try {
			notifications = await api.listNotifications();
			error = null;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load notifications.';
		}
	}

	async function markRead(id: string) {
		notifications = notifications.map((n) => (n.id === id ? { ...n, read: true } : n));
		try {
			await api.markNotificationRead(id);
		} catch {
			// A stale unread flag self-corrects on the next load/tick.
		}
	}

	async function markAllRead() {
		notifications = notifications.map((n) => ({ ...n, read: true }));
		try {
			await api.markAllNotificationsRead();
		} catch {
			// Same as above — non-fatal.
		}
	}

	function toggle() {
		open = !open;
	}

	onMount(() => {
		load();
		return connectLiveSocket<NotificationOut>('/ws/notifications', (event) => {
			notifications = [event, ...notifications].slice(0, 50);
		});
	});
</script>

<div class="relative">
	<button
		onclick={toggle}
		class="relative rounded-full p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
		aria-label="Notifications"
	>
		<Icon name="bell" class="h-5 w-5" />
		{#if unreadCount > 0}
			<span
				class="absolute -top-0.5 -right-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-semibold text-white"
			>
				{unreadCount > 9 ? '9+' : unreadCount}
			</span>
		{/if}
	</button>

	{#if open}
		<button
			class="fixed inset-0 z-10 cursor-default"
			aria-label="Close notifications"
			onclick={() => (open = false)}
		></button>
		<div
			class="absolute right-0 z-20 mt-2 w-80 rounded border border-slate-200 bg-white shadow-lg dark:border-slate-800 dark:bg-slate-900"
		>
			<div
				class="flex items-center justify-between border-b border-slate-200 px-3 py-2 dark:border-slate-800"
			>
				<span class="text-sm font-semibold">Notifications</span>
				{#if unreadCount > 0}
					<button
						onclick={markAllRead}
						class="text-xs text-sky-600 hover:underline dark:text-sky-400"
					>
						Mark all read
					</button>
				{/if}
			</div>
			<div class="max-h-96 overflow-y-auto">
				{#if error}
					<p class="p-3 text-xs text-rose-600 dark:text-rose-400">{error}</p>
				{:else if notifications.length === 0}
					<p class="p-4 text-center text-xs text-slate-400">No notifications yet.</p>
				{:else}
					{#each notifications as notification (notification.id)}
						<button
							onclick={() => markRead(notification.id)}
							class="block w-full border-b border-slate-100 px-3 py-2 text-left last:border-0 hover:bg-slate-50 dark:border-slate-800/60 dark:hover:bg-slate-800/60 {notification.read
								? 'opacity-60'
								: ''}"
						>
							<div class="flex items-center justify-between gap-2">
								<span
									class="rounded-full px-2 py-0.5 text-[10px] font-medium {TYPE_COLOR[
										notification.type
									] ?? ''}"
								>
									{TYPE_LABEL[notification.type] ?? notification.type}
								</span>
								<span class="text-[10px] text-slate-400"
									>{formatDateTime(notification.created_at)}</span
								>
							</div>
							<p class="mt-1 text-xs text-slate-700 dark:text-slate-300">{notification.message}</p>
						</button>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>
