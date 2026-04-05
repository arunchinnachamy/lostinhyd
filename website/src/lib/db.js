// D1 Database utilities with caching for Cloudflare Pages
// Access D1 via Astro.locals.runtime.env.DB binding

const CACHE_TTL = 2 * 60 * 60; // 2 hours in seconds

// Helper to fetch with caching
async function fetchWithCache(caches, cacheKey, fetchFn, ttl = CACHE_TTL) {
  // Try to get from cache first
  if (caches) {
    const cache = caches.default;
    const cached = await cache.match(cacheKey);
    if (cached) {
      return await cached.json();
    }
  }
  
  // Fetch fresh data
  const data = await fetchFn();
  
  // Store in cache
  if (caches && data) {
    const cache = caches.default;
    const response = new Response(JSON.stringify(data), {
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': `max-age=${ttl}`
      }
    });
    await cache.put(cacheKey, response);
  }
  
  return data;
}

// Get database from environment
function getDB(context) {
  const env = context?.locals?.runtime?.env || {};
  return env.DB;
}

// Get all published events
export async function getEvents(context, limit = 50, offset = 0) {
  const db = getDB(context);
  if (!db) return [];
  
  const cacheKey = `events:list:${limit}:${offset}`;
  const caches = context?.runtime?.caches;
  
  return fetchWithCache(caches, cacheKey, async () => {
    const { results } = await db.prepare(`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        v.latitude,
        v.longitude,
        (SELECT GROUP_CONCAT(c.name) 
         FROM event_categories ec 
         JOIN categories c ON ec.category_id = c.id 
         WHERE ec.event_id = e.id) as categories
      FROM events e
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE e.status = 'published'
        AND (e.end_date IS NULL OR e.end_date >= date('now'))
      GROUP BY e.id
      ORDER BY e.start_date ASC, e.start_time ASC
      LIMIT ? OFFSET ?
    `).bind(limit, offset).all();
    
    return results || [];
  });
}

// Get featured events
export async function getFeaturedEvents(context, limit = 6) {
  const db = getDB(context);
  if (!db) return [];
  
  const cacheKey = `events:featured:${limit}`;
  const caches = context?.runtime?.caches;
  
  return fetchWithCache(caches, cacheKey, async () => {
    const { results } = await db.prepare(`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        (SELECT GROUP_CONCAT(c.name) 
         FROM event_categories ec 
         JOIN categories c ON ec.category_id = c.id 
         WHERE ec.event_id = e.id) as categories
      FROM events e
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE e.status = 'published'
        AND e.is_featured = 1
        AND (e.end_date IS NULL OR e.end_date >= date('now'))
      GROUP BY e.id
      ORDER BY e.start_date ASC
      LIMIT ?
    `).bind(limit).all();
    
    return results || [];
  });
}

// Get single event by slug
export async function getEventBySlug(context, slug) {
  const db = getDB(context);
  if (!db) return null;
  
  // Don't cache single event pages (may change frequently)
  const { results } = await db.prepare(`
    SELECT 
      e.*,
      v.name as venue_name_full,
      v.address as venue_address_full,
      v.area,
      v.city,
      v.latitude,
      v.longitude,
      v.phone as venue_phone,
      v.website as venue_website,
      (SELECT GROUP_CONCAT(c.name) 
       FROM event_categories ec 
       JOIN categories c ON ec.category_id = c.id 
       WHERE ec.event_id = e.id) as categories
    FROM events e
    LEFT JOIN venues v ON e.venue_id = v.id
    WHERE e.slug = ?
      AND e.status = 'published'
    LIMIT 1
  `).bind(slug).all();
  
  return results?.[0] || null;
}

// Get all categories
export async function getCategories(context) {
  const db = getDB(context);
  if (!db) return [];
  
  const cacheKey = 'categories:all';
  const caches = context?.runtime?.caches;
  
  return fetchWithCache(caches, cacheKey, async () => {
    const { results } = await db.prepare(`
      SELECT 
        c.*,
        COUNT(e.id) as event_count
      FROM categories c
      LEFT JOIN event_categories ec ON c.id = ec.category_id
      LEFT JOIN events e ON ec.event_id = e.id AND e.status = 'published'
      WHERE c.is_active = 1
      GROUP BY c.id
      ORDER BY c.display_order ASC, c.name ASC
    `).all();
    
    return results || [];
  }, 4 * 60 * 60); // Cache categories for 4 hours
}

// Get category by slug
export async function getCategoryBySlug(context, slug) {
  const db = getDB(context);
  if (!db) return null;
  
  const { results } = await db.prepare(`
    SELECT * FROM categories
    WHERE slug = ? AND is_active = 1
    LIMIT 1
  `).bind(slug).all();
  
  return results?.[0] || null;
}

// Get events by category
export async function getEventsByCategory(context, categorySlug, limit = 50) {
  const db = getDB(context);
  if (!db) return [];
  
  const cacheKey = `events:category:${categorySlug}:${limit}`;
  const caches = context?.runtime?.caches;
  
  return fetchWithCache(caches, cacheKey, async () => {
    const { results } = await db.prepare(`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        (SELECT GROUP_CONCAT(c2.name) 
         FROM event_categories ec2 
         JOIN categories c2 ON ec2.category_id = c2.id 
         WHERE ec2.event_id = e.id) as categories
      FROM events e
      INNER JOIN event_categories ec ON e.id = ec.event_id
      INNER JOIN categories c ON ec.category_id = c.id
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE c.slug = ?
        AND e.status = 'published'
        AND (e.end_date IS NULL OR e.end_date >= date('now'))
      GROUP BY e.id
      ORDER BY e.start_date ASC, e.start_time ASC
      LIMIT ?
    `).bind(categorySlug, limit).all();
    
    return results || [];
  });
}

// Get all active sources
export async function getSources(context) {
  const db = getDB(context);
  if (!db) return [];
  
  const { results } = await db.prepare(`
    SELECT * FROM sources
    WHERE is_active = 1
    ORDER BY name ASC
  `).all();
  
  return results || [];
}

// Utility: Purge cache for specific patterns
export async function purgeCache(context, pattern) {
  const caches = context?.runtime?.caches;
  if (!caches) return;
  
  const cache = caches.default;
  // Note: Cloudflare Cache API doesn't support pattern matching
  // For full purge, use Cloudflare API or Purge Everything in dashboard
  // This is a placeholder for future implementation
}
