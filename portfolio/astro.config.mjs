// @ts-check
import { defineConfig } from 'astro/config';

import mdx from '@astrojs/mdx';

// https://astro.build/config
export default defineConfig({
  // Build output goes to the default ./dist — never docs/ (that's the live site).
  site: 'https://dnesting.com',

  integrations: [mdx()]
});