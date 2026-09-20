<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';

	let { children } = $props();

	const navItems = [
		{ href: resolve('/'), label: 'Overview' },
		{ href: resolve('/scanner'), label: 'Scanner' },
		{ href: resolve('/positions'), label: 'Positions' },
		{ href: resolve('/history'), label: 'History' },
		{ href: resolve('/prices'), label: 'Prices' },
		{ href: resolve('/risk'), label: 'Position Size' },
		{ href: resolve('/settings'), label: 'Settings' }
	];
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
	<header class="border-b border-slate-200 dark:border-slate-800">
		<div class="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
			<a href={resolve('/')} class="text-lg font-semibold tracking-tight">Forex AI Market Scanner</a
			>
			<nav class="flex flex-wrap gap-4 text-sm">
				{#each navItems as item (item.href)}
					<a
						href={item.href}
						class="rounded px-2 py-1 transition-colors {page.url.pathname === item.href
							? 'bg-slate-200 font-medium dark:bg-slate-800'
							: 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-100'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>
		</div>
	</header>
	<main class="mx-auto max-w-6xl px-4 py-6">
		{@render children()}
	</main>
	<footer class="mx-auto max-w-6xl px-4 pb-6 text-xs text-slate-400">
		Conditional analysis only — not a trade recommendation. No setup is valid until its stated
		confirmation and risk checks pass.
	</footer>
</div>
