import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const newsletter = defineCollection({
	// Load Markdown and MDX files in the `src/content/newsletter/` directory.
	loader: glob({ base: './src/content/newsletter', pattern: '**/*.{md,mdx}' }),
	// Type-check frontmatter using a schema
	schema: ({ image }) =>
		z.object({
			title: z.string(),
			description: z.string(),
			// Transform string to Date object
			pubDate: z.coerce.date(),
			updatedDate: z.coerce.date().optional(),
			heroImage: z.optional(image()),
			// SEO fields
			keywords: z.array(z.string()).optional(),
			author: z.string().optional(),
			// Categories for filtering
			category: z.enum(['food', 'events', 'places', 'culture', 'shopping']).optional(),
			area: z.string().optional(), // Hyderabad area (Banjara Hills, Old City, etc.)
			featured: z.boolean().default(false),
		}),
});

const events = defineCollection({
	loader: glob({ base: './src/content/events', pattern: '**/*.{md,mdx}' }),
	schema: ({ image }) =>
		z.object({
			title: z.string(),
			description: z.string(),
			eventDate: z.coerce.date(),
			location: z.string(),
			area: z.string(),
			venue: z.string().optional(),
			price: z.string().optional(),
			link: z.string().url().optional(),
			heroImage: z.optional(image()),
			tags: z.array(z.string()).optional(),
			source: z.string().optional(), // Where we found this event
		}),
});

const places = defineCollection({
	loader: glob({ base: './src/content/places', pattern: '**/*.{md,mdx}' }),
	schema: ({ image }) =>
		z.object({
			name: z.string(),
			description: z.string(),
			area: z.string(),
			address: z.string().optional(),
			mapLink: z.string().url().optional(),
			category: z.enum(['cafe', 'restaurant', 'attraction', 'park', 'market', 'museum', 'other']),
			tags: z.array(z.string()).optional(),
			heroImage: z.optional(image()),
			featured: z.boolean().default(false),
			bestTime: z.string().optional(),
			mustTry: z.string().optional(),
		}),
});

export const collections = { newsletter, events, places };
