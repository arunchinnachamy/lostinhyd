// @ts-check

import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	site: 'https://lostinhyd.pages.dev',
	integrations: [mdx(), sitemap()],
	output: 'static',
	build: {
		format: 'file'
	},
	// SEO optimizations
	vite: {
		build: {
			cssCodeSplit: true,
			rollupOptions: {
				output: {
					manualChunks: undefined
				}
			}
		}
	}
});
