import postgres from 'postgres';

// Database URL must be set via environment variable
const DATABASE_URL = import.meta.env.DATABASE_URL || process.env.DATABASE_URL;

// Check if we have a database URL
const hasDatabase = !!DATABASE_URL;

// Create postgres client (only if URL is available)
export function createClient() {
  if (!DATABASE_URL) {
    throw new Error('DATABASE_URL environment variable is required');
  }
  
  return postgres(DATABASE_URL, {
    ssl: 'require',
    connect_timeout: 30,
    idle_timeout: 20,
    max_lifetime: 60 * 30,
  });
}

// Mock data for when database is not available
const mockCategories = [
  { id: 1, name: 'Music', slug: 'music', event_count: 0 },
  { id: 2, name: 'Food & Drink', slug: 'food-drink', event_count: 0 },
  { id: 3, name: 'Arts & Culture', slug: 'arts-culture', event_count: 0 },
  { id: 4, name: 'Tech', slug: 'tech', event_count: 0 },
  { id: 5, name: 'Sports', slug: 'sports', event_count: 0 },
];

// Get all published events
export async function getEvents(limit = 50, offset = 0) {
  if (!hasDatabase) return [];
  
  const sql = createClient();
  try {
    const events = await sql`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        v.latitude,
        v.longitude,
        array_agg(c.name) as categories
      FROM lostinhyd.events e
      LEFT JOIN lostinhyd.venues v ON e.venue_id = v.id
      LEFT JOIN lostinhyd.event_categories ec ON e.id = ec.event_id
      LEFT JOIN lostinhyd.categories c ON ec.category_id = c.id
      WHERE e.status = 'published'
        AND (e.end_date IS NULL OR e.end_date >= CURRENT_DATE)
      GROUP BY e.id, v.name, v.area, v.latitude, v.longitude
      ORDER BY e.start_date ASC, e.start_time ASC
      LIMIT ${limit} OFFSET ${offset}
    `;
    return events;
  } catch (e) {
    console.error('Database error:', e);
    return [];
  } finally {
    await sql.end();
  }
}

// Get featured events
export async function getFeaturedEvents(limit = 6) {
  if (!hasDatabase) return [];
  
  const sql = createClient();
  try {
    const events = await sql`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        array_agg(c.name) as categories
      FROM lostinhyd.events e
      LEFT JOIN lostinhyd.venues v ON e.venue_id = v.id
      LEFT JOIN lostinhyd.event_categories ec ON e.id = ec.event_id
      LEFT JOIN lostinhyd.categories c ON ec.category_id = c.id
      WHERE e.status = 'published'
        AND e.is_featured = true
        AND (e.end_date IS NULL OR e.end_date >= CURRENT_DATE)
      GROUP BY e.id, v.name, v.area
      ORDER BY e.start_date ASC
      LIMIT ${limit}
    `;
    return events;
  } catch (e) {
    console.error('Database error:', e);
    return [];
  } finally {
    await sql.end();
  }
}

// Get single event by slug
export async function getEventBySlug(slug) {
  if (!hasDatabase) return null;
  
  const sql = createClient();
  try {
    const [event] = await sql`
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
        array_agg(c.name) as categories
      FROM lostinhyd.events e
      LEFT JOIN lostinhyd.venues v ON e.venue_id = v.id
      LEFT JOIN lostinhyd.event_categories ec ON e.id = ec.event_id
      LEFT JOIN lostinhyd.categories c ON ec.category_id = c.id
      WHERE e.slug = ${slug}
        AND e.status = 'published'
      GROUP BY e.id, v.name, v.address, v.area, v.city, v.latitude, v.longitude, v.phone, v.website
    `;
    return event;
  } catch (e) {
    console.error('Database error:', e);
    return null;
  } finally {
    await sql.end();
  }
}

// Get all categories
export async function getCategories() {
  if (!hasDatabase) return mockCategories;
  
  const sql = createClient();
  try {
    const categories = await sql`
      SELECT 
        c.*,
        COUNT(e.id) as event_count
      FROM lostinhyd.categories c
      LEFT JOIN lostinhyd.event_categories ec ON c.id = ec.category_id
      LEFT JOIN lostinhyd.events e ON ec.event_id = e.id AND e.status = 'published'
      WHERE c.is_active = true
      GROUP BY c.id
      ORDER BY c.display_order ASC, c.name ASC
    `;
    return categories;
  } catch (e) {
    console.error('Database error:', e);
    return mockCategories;
  } finally {
    await sql.end();
  }
}

// Get category by slug
export async function getCategoryBySlug(slug) {
  if (!hasDatabase) return null;
  
  const sql = createClient();
  try {
    const [category] = await sql`
      SELECT * FROM lostinhyd.categories
      WHERE slug = ${slug} AND is_active = true
    `;
    return category;
  } catch (e) {
    console.error('Database error:', e);
    return null;
  } finally {
    await sql.end();
  }
}

// Get events by category
export async function getEventsByCategory(categorySlug, limit = 50) {
  if (!hasDatabase) return [];
  
  const sql = createClient();
  try {
    const events = await sql`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        array_agg(c2.name) as categories
      FROM lostinhyd.events e
      INNER JOIN lostinhyd.event_categories ec ON e.id = ec.event_id
      INNER JOIN lostinhyd.categories c ON ec.category_id = c.id
      LEFT JOIN lostinhyd.venues v ON e.venue_id = v.id
      LEFT JOIN lostinhyd.event_categories ec2 ON e.id = ec2.event_id
      LEFT JOIN lostinhyd.categories c2 ON ec2.category_id = c2.id
      WHERE c.slug = ${categorySlug}
        AND e.status = 'published'
        AND (e.end_date IS NULL OR e.end_date >= CURRENT_DATE)
      GROUP BY e.id, v.name, v.area
      ORDER BY e.start_date ASC, e.start_time ASC
      LIMIT ${limit}
    `;
    return events;
  } catch (e) {
    console.error('Database error:', e);
    return [];
  } finally {
    await sql.end();
  }
}

// Get all active sources
export async function getSources() {
  if (!hasDatabase) return [];
  
  const sql = createClient();
  try {
    const sources = await sql`
      SELECT * FROM lostinhyd.sources
      WHERE is_active = true
      ORDER BY name ASC
    `;
    return sources;
  } catch (e) {
    console.error('Database error:', e);
    return [];
  } finally {
    await sql.end();
  }
}
