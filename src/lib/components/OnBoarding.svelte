<script>
	import { getContext, onMount } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_BASE_URL } from '$lib/constants';

	import Marquee from './common/Marquee.svelte';
	import SlideShow from './common/SlideShow.svelte';
	import ArrowRightCircle from './icons/ArrowRightCircle.svelte';

	export let show = true;
	export let getStartedHandler = () => {};

	function setLogoImage() {
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;

				darkImage.onload = () => {
					logo.src = `${WEBUI_BASE_URL}/static/favicon-dark.png`;
					logo.style.filter = ''; // Ensure no inversion is applied if splash-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if splash-dark.png is missing
				};
			}
		}
	}

	$: if (show) {
		setLogoImage();
	}
</script>

{#if show}
	<div class="w-full min-h-screen relative bg-white text-black font-sans overflow-hidden">
		<!-- Navbar -->
		<header
			class="flex items-center justify-between px-6 lg:px-16 py-1 -20 relative border border-[#6D24D147] rounded-[75px] w-[calc(100%-40px)] mx-auto mt-[35px]"
		>
			<div class="flex items-center gap-3">
				<img id="logo" crossorigin="anonymous" src="/favicon.png" alt="logo" class="w-[38px] h-[38px]" />
				<div>
					<div class="font-bold text-lg">Beagle</div>
					<div class="text-xs text-gray-500">Your AI Assistant</div>
				</div>
			</div>

			<div class="flex items-center space-x-4">
				<a href="https://www.linkedin.com/company/histofy/">
					<img crossorigin="anonymous" src="/assets/images/linked-in.svg" alt="logo" />
				</a>
				<button
					on:click={() => getStartedHandler()}
					class="text-xs text-white border bg-purple-100 hover:bg-purple-50 border-purple-100 px-3 py-1 rounded-full hover:bg-purple-50 transition"
				>
					{$i18n.t('Sign In')}
				</button>
			</div>
		</header>

		<!-- Hero Section with background image -->
		<section
			class="relative z-10 text-center px-6 lg:px-20 py-20 lg:py-32 bg-white h-[calc(100vh-110px)] overflow-hidden"
		>
			<!-- Decorative image with reduced opacity -->
			<img
				src="/assets/images/hero-bg.png"
				alt="Background"
				class="absolute top-45 left-1/2 -translate-x-1/2 opacity-100 w-[700px] max-w-full z-0 pointer-events-none"
			/>

			<!-- Foreground content -->
			<h1 class="relative z-10 text-3xl lg:text-5xl font-bold leading-tight text-black font-nexa">
				{$i18n.t('Next-Gen')}
				<span class="text-purple-600">{$i18n.t('ToxPath Study Reporting')}</span><br />
				{$i18n.t('Interrograte. Integrate. Accelerate.')}
			</h1>

			<div class="mt-8 relative z-10">
				<button
					on:click={() => getStartedHandler()}
					class="inline-flex items-center justify-center bg-gradient-to-r from-purple-600 to-purple-400 text-white px-8 py-3 rounded-full text-sm font-medium shadow-md transition"
				>
					{$i18n.t('Get Started')}
				</button>
			</div>

			<video
				src="/assets/videos/animated.mp4"
				autoplay
				muted
				loop
				playsinline
				class="absolute bottom-10 left-1/2 transform -translate-x-1/2 z-3 pointer-events-none w-[500px] h-[500px] rounded-full object-cover opacity-40"
			/>
			<div
				class="absolute bottom-10 right-4 left-4 flex items-center justify-between z-0 hidden md:flex"
			>
				<img src="/assets/images/Union.png" alt="Decoration Bottom Right 1" />
				<img src="/assets/images/Union2.png" alt="Decoration Top Left" />
			</div>
		</section>

		<!-- Decorative animated video orb -->

		<!-- Corner decorations with images -->

		<!-- Corner decorations with images hidden on sm and xs -->
	</div>
{/if}
