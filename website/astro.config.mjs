import { defineConfig } from 'astro/config';
import cloudflare from '@astrojs/cloudflare';

// https://astro.build/config
export default defineConfig({
  output: 'hybrid',  // Changed from 'server' to 'hybrid' for static + dynamic
  adapter: cloudflare(),
  site: 'https://lostinhyd.pages.dev',
  trailingSlash: 'always',
  build: {
    format: 'directory'
  },
  vite: {
    define: {
      'import.meta.env.DATABASE_URL': JSON.stringify(process.env.DATABASE_URL)
    }
  }
});
