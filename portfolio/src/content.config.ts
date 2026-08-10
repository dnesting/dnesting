import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

// ONE showcase project per .mdx file. Frontmatter drives the tile + the modal
// chrome (eyebrow/title/tagline/CTA/gallery/chips); the Markdown BODY is the
// modal write-up, authored as real Markdown. Drop `<ArchDiagram name="…"/>`
// inline in the body wherever the architecture diagram belongs.
const projects = defineCollection({
  loader: glob({ pattern: '**/*.mdx', base: './src/content/projects' }),
  schema: z.object({
    title: z.string(),
    // Modal sub-headline (`.m-tag`).
    tagline: z.string(),
    kind: z.enum(['Live demo', 'Details', 'In progress']),
    // Short text shown ON the tile (`.tile .t p`).
    blurb: z.string(),
    // Tile cover-art key → `cov-<cover>` class + keyed inline art.
    cover: z.enum(['shot', 't', 's', 'm']),
    demoUrl: z.string().optional(),
    demoNote: z.string().optional(),
    gallery: z.array(z.object({ src: z.string(), alt: z.string() })).optional(),
    video: z.object({ src: z.string(), cap: z.string() }).optional(),
    chips: z.array(z.string()),
  }),
});

export const collections = { projects };
