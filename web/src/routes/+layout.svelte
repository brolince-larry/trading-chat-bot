<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { page } from '$app/state';
	import { resolve } from '$app/paths';

	let { children } = $props();

	const navItems = [
		{ href: resolve('/'), label: 'Scanner' },
		{ href: resolve('/risk'), label: 'Position Size' }
	];
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
	<header class="border-b border-slate-200 dark:border-slate-800">
		<div class="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
			<a href={resolve('/')} class="text-lg font-semibold tracking-tight">Forex AI Market Scanner</a
			>
			<nav class="flex gap-4 text-sm">
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
