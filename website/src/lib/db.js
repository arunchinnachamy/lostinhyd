// Database utilities with Cloudflare Workers compatibility
// Note: Using mock data since postgres library doesn't work in Cloudflare Workers

// Mock data for categories
const mockCategories = [
  { id: 1, name: 'Music', slug: 'music', description: 'Concerts and live music', event_count: 0, display_order: 1, is_active: true },
  { id: 2, name: 'Food & Drink', slug: 'food-drink', description: 'Food festivals and tastings', event_count: 0, display_order: 2, is_active: true },
  { id: 3, name: 'Arts & Culture', slug: 'arts-culture', description: 'Art exhibitions and cultural events', event_count: 0, display_order: 3, is_active: true },
  { id: 4, name: 'Tech', slug: 'tech', description: 'Tech meetups and workshops', event_count: 0, display_order: 4, is_active: true },
  { id: 5, name: 'Sports', slug: 'sports', description: 'Sports events and fitness', event_count: 0, display_order: 5, is_active: true },
  { id: 6, name: 'Networking', slug: 'networking', description: 'Professional networking', event_count: 0, display_order: 6, is_active: true },
  { id: 7, name: 'Comedy', slug: 'comedy', description: 'Stand-up and comedy shows', event_count: 0, display_order: 7, is_active: true },
  { id: 8, name: 'Movies', slug: 'movies', description: 'Film screenings and cinema', event_count: 0, display_order: 8, is_active: true },
];

// Mock events data
const mockEvents = [
  {
    id: 1,
    title: "Weekend Music Festival",
    slug: "weekend-music-festival",
    description: "Join us for a weekend of amazing live music performances featuring local and international artists.",
    start_date: "2026-04-15",
    start_time: "18:00:00",
    end_date: "2026-04-17",
    end_time: "23:00:00",
    venue_name: "Gachibowli Stadium",
    area: "Gachibowli",
    is_free: false,
    price_min: 500,
    price_max: 2000,
    currency: "INR",
    is_featured: true,
    image_url: null,
    categories: ["Music"],
    status: "published"
  },
  {
    id: 2,
    title: "Tech Startup Meetup",
    slug: "tech-startup-meetup",
    description: "Network with Hyderabad's best tech entrepreneurs and investors. Perfect for startups and developers.",
    start_date: "2026-04-20",
    start_time: "19:00:00",
    end_date: null,
    end_time: "21:00:00",
    venue_name: "WeWork Hitech City",
    area: "Hitech City",
    is_free: true,
    price_min: null,
    price_max: null,
    currency: "INR",
    is_featured: true,
    image_url: null,
    categories: ["Tech", "Networking"],
    status: "published"
  },
  {
    id: 3,
    title: "Food & Wine Tasting",
    slug: "food-wine-tasting",
    description: "Experience the finest culinary delights paired with exquisite wines from around the world.",
    start_date: "2026-04-25",
    start_time: "17:00:00",
    end_date: null,
    end_time: "20:00:00",
    venue_name: "Park Hyatt Hyderabad",
    area: "Banjara Hills",
    is_free: false,
    price_min: 1500,
    price_max: 3000,
    currency: "INR",
    is_featured: true,
    image_url: null,
    categories: ["Food & Drink"],
    status: "published"
  }
];

// Get all published events
export async function getEvents(limit = 50, offset = 0) {
  return mockEvents.slice(offset, offset + limit);
}

// Get featured events
export async function getFeaturedEvents(limit = 6) {
  return mockEvents.filter(e => e.is_featured).slice(0, limit);
}

// Get single event by slug
export async function getEventBySlug(slug) {
  return mockEvents.find(e => e.slug === slug) || null;
}

// Get all categories
export async function getCategories() {
  return mockCategories;
}

// Get category by slug
export async function getCategoryBySlug(slug) {
  return mockCategories.find(c => c.slug === slug) || null;
}

// Get events by category
export async function getEventsByCategory(categorySlug, limit = 50) {
  return mockEvents.filter(e => 
    e.categories.some(c => c.toLowerCase().replace(/ & /g, '-').replace(/ /g, '-') === categorySlug)
  ).slice(0, limit);
}

// Get all active sources
export async function getSources() {
  return [];
}
