<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import Icon from '$lib/components/Icon.svelte';
	import NotificationBell from '$lib/components/NotificationBell.svelte';

	let { children } = $props();

	const primaryNav = [
		{ href: resolve('/'), label: 'Dashboard', icon: 'dashboard' },
		{ href: resolve('/scanner'), label: 'Markets', icon: 'markets' },
		{ href: resolve('/bot'), label: 'Trading Bot', icon: 'bot' },
		{ href: resolve('/positions'), label: 'Portfolio', icon: 'portfolio' },
		{ href: resolve('/risk-management'), label: 'Risk Management', icon: 'shield' },
		{ href: resolve('/automations'), label: 'Automations', icon: 'zap' },
		{ href: resolve('/analytics'), label: 'Analytics', icon: 'analytics' },
		{ href: resolve('/history'), label: 'Reports', icon: 'reports' },
		{ href: resolve('/settings'), label: 'Settings', icon: 'settings' }
	];

	const toolsNav = [
		{ href: resolve('/prices'), label: 'Live Prices', icon: 'dollar' },
		{ href: resolve('/risk'), label: 'Position Size', icon: 'calculator' },
		{ href: resolve('/backtest'), label: 'Backtest', icon: 'history' }
	];

	let mobileNavOpen = $state(false);
	let searchValue = $state('');
	let isDark = $state(
		typeof document !== 'undefined' && document.documentElement.classList.contains('dark')
	);

	function isActive(href: string): boolean {
		return href === resolve('/') ? page.url.pathname === href : page.url.pathname.startsWith(href);
	}

	function toggleTheme() {
		isDark = !isDark;
		document.documentElement.classList.toggle('dark', isDark);
		try {
			localStorage.setItem('theme', isDark ? 'dark' : 'light');
		} catch {
			// Private-browsing/blocked storage — theme just won't persist across reloads.
		}
	}

	function submitSearch(event: SubmitEvent) {
		event.preventDefault();
		const symbol = searchValue
			.trim()
			.toUpperCase()
			.replace(/[\s-]+/g, '_');
		if (!symbol) return;
		mobileNavOpen = false;
		searchValue = '';
		goto(resolve('/analysis/[symbol]', { symbol }));
	}
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
	<div class="flex">
		<!-- Desktop sidebar -->
		<aside
			class="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex dark:border-slate-800 dark:bg-slate-900"
		>
			<a
				href={resolve('/')}
				class="flex items-center gap-2 border-b border-slate-200 px-4 py-4 dark:border-slate-800"
			>
				<span
					class="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white dark:bg-white dark:text-slate-900"
				>
					<Icon name="markets" class="h-4 w-4" />
				</span>
				<span class="text-sm font-semibold tracking-tight">Forex AI Scanner</span>
			</a>
			<nav class="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
				{#each primaryNav as item (item.href)}
					<a
						href={item.href}
						class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors {isActive(
							item.href
						)
							? 'bg-slate-900 font-medium text-white dark:bg-white dark:text-slate-900'
							: 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
					>
						<Icon name={item.icon} class="h-4 w-4 shrink-0" />
						{item.label}
					</a>
				{/each}
				<div class="mt-3 border-t border-slate-200 pt-3 dark:border-slate-800">
					<p class="px-3 pb-1 text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
						Tools
					</p>
					{#each toolsNav as item (item.href)}
						<a
							href={item.href}
							class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors {isActive(
								item.href
							)
								? 'bg-slate-900 font-medium text-white dark:bg-white dark:text-slate-900'
								: 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'}"
						>
							<Icon name={item.icon} class="h-4 w-4 shrink-0" />
							{item.label}
						</a>
					{/each}
				</div>
			</nav>
			<div
				class="border-t border-slate-200 px-4 py-3 text-[11px] text-slate-400 dark:border-slate-800"
			>
				Conditional analysis only — not a trade recommendation.
			</div>
		</aside>

		<!-- Mobile drawer -->
		{#if mobileNavOpen}
			<button
				class="fixed inset-0 z-30 bg-black/40 lg:hidden"
				aria-label="Close menu"
				onclick={() => (mobileNavOpen = false)}
			></button>
			<aside
				class="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-white lg:hidden dark:bg-slate-900"
			>
				<div
					class="flex items-center justify-between border-b border-slate-200 px-4 py-4 dark:border-slate-800"
				>
					<span class="text-sm font-semibold">Forex AI Scanner</span>
					<button onclick={() => (mobileNavOpen = false)} aria-label="Close menu">
						<Icon name="x" class="h-5 w-5" />
					</button>
				</div>
				<nav class="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-3">
					{#each [...primaryNav, ...toolsNav] as item (item.href)}
						<a
							href={item.href}
							onclick={() => (mobileNavOpen = false)}
							class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm {isActive(item.href)
								? 'bg-slate-900 font-medium text-white dark:bg-white dark:text-slate-900'
								: 'text-slate-600 dark:text-slate-400'}"
						>
							<Icon name={item.icon} class="h-4 w-4 shrink-0" />
							{item.label}
						</a>
					{/each}
				</nav>
			</aside>
		{/if}

		<div class="flex min-h-screen flex-1 flex-col">
			<header
				class="sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80"
			>
				<div class="flex items-center gap-3 px-4 py-3">
					<button
						class="rounded p-1.5 text-slate-500 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800"
						onclick={() => (mobileNavOpen = true)}
						aria-label="Open menu"
					>
						<Icon name="menu" class="h-5 w-5" />
					</button>
					<form onsubmit={submitSearch} class="relative max-w-sm flex-1">
						<Icon
							name="search"
							class="pointer-events-none absolute top-2.5 left-3 h-4 w-4 text-slate-400"
						/>
						<input
							type="text"
							bind:value={searchValue}
							placeholder="Jump to a pair, e.g. EUR_USD…"
							class="w-full rounded-lg border border-slate-300 bg-slate-50 py-2 pr-3 pl-9 text-sm outline-none focus:border-slate-400 dark:border-slate-700 dark:bg-slate-900"
						/>
					</form>
					<div class="ml-auto flex items-center gap-1">
						<NotificationBell />
						<button
							onclick={toggleTheme}
							class="rounded-full p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800"
							aria-label="Toggle theme"
						>
							<Icon name={isDark ? 'sun' : 'moon'} class="h-5 w-5" />
						</button>
					</div>
				</div>
			</header>
			<main class="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
				{@render children()}
			</main>
			<footer class="mx-auto w-full max-w-6xl px-4 pb-6 text-xs text-slate-400">
				Conditional analysis only — not a trade recommendation. No setup is valid until its stated
				confirmation and risk checks pass.
			</footer>
		</div>
	</div>
</div>
