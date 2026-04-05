import { defineConfig } from 'astro/config';
import cloudflare from '@astrojs/cloudflare';

// https://astro.build/config
export default defineConfig({
  output: 'static',
  adapter: cloudflare({
    mode: 'directory',
    functionPerRoute: true,
    runtime: {
      mode: 'local'
    }
  }),
  site: 'https://lostinhyd.pages.dev',
  trailingSlash: 'always',
  build: {
    format: 'directory'
  }
});
