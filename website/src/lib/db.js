import postgres from 'postgres';

// Database URL must be set via environment variable
const DATABASE_URL = import.meta.env.DATABASE_URL || process.env.DATABASE_URL;

if (!DATABASE_URL) {
  throw new Error('DATABASE_URL environment variable is required');
}

// Create postgres client
export function createClient() {
  return postgres(DATABASE_URL, {
    ssl: 'require',
    connect_timeout: 30,
    idle_timeout: 20,
    max_lifetime: 60 * 30,
  });
}

// Get all published events
export async function getEvents(limit = 50, offset = 0) {
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
  } finally {
    await sql.end();
  }
}

// Get featured events
export async function getFeaturedEvents(limit = 6) {
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
  } finally {
    await sql.end();
  }
}

// Get single event by slug
export async function getEventBySlug(slug) {
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
  } finally {
    await sql.end();
  }
}

// Get all categories
export async function getCategories() {
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
  } finally {
    await sql.end();
  }
}

// Get category by slug
export async function getCategoryBySlug(slug) {
  const sql = createClient();
  try {
    const [category] = await sql`
      SELECT * FROM lostinhyd.categories
      WHERE slug = ${slug} AND is_active = true
    `;
    return category;
  } finally {
    await sql.end();
  }
}

// Get events by category
export async function getEventsByCategory(categorySlug, limit = 50) {
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
  } finally {
    await sql.end();
  }
}

// Get all active sources
export async function getSources() {
  const sql = createClient();
  try {
    const sources = await sql`
      SELECT * FROM lostinhyd.sources
      WHERE is_active = true
      ORDER BY name ASC
    `;
    return sources;
  } finally {
    await sql.end();
  }
}
