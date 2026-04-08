import { defineConfig } from 'astro/config';
import node from '@astrojs/node';

// https://astro.build/config
export default defineConfig({
  output: 'server',
  adapter: node({
    mode: 'standalone'
  }),
  site: process.env.SITE_URL || 'http://localhost',
  trailingSlash: 'always',
  build: {
    format: 'directory'
  }
});
