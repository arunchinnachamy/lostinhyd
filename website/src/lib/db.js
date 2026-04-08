// PostgreSQL Database utilities for Lost in Hyd
// Connects to OVH managed PostgreSQL

import pg from 'pg';

const { Pool } = pg;

// Create a connection pool
function createPool() {
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) {
    throw new Error('DATABASE_URL environment variable is required');
  }

  const isOvh = databaseUrl.includes('ovh.net');
  const connectionString = isOvh
    ? databaseUrl.replace(/[?&]sslmode=[^&]*/, '')
    : databaseUrl;

  return new Pool({
    connectionString,
    ssl: isOvh ? { rejectUnauthorized: false } : false,
    max: 10,
    idleTimeoutMillis: 30000,
    connectionTimeoutMillis: 5000,
  });
}

let pool = null;

function getPool() {
  if (!pool) {
    pool = createPool();
  }
  return pool;
}

// Execute a query with retry logic
async function queryWithRetry(sql, params, retries = 3) {
  const pool = getPool();
  let lastError;

  for (let i = 0; i < retries; i++) {
    let client;
    try {
      client = await pool.connect();
      await client.query('SET search_path TO lostinhyd, public');
      const result = await client.query(sql, params);
      return result;
    } catch (error) {
      lastError = error;
      console.error(`Query attempt ${i + 1} failed:`, error.message);
      
      // Exponential backoff
      if (i < retries - 1) {
        await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)));
      }
    } finally {
      if (client) {
        client.release();
      }
    }
  }

  throw lastError;
}

// Get all published events
export async function getEvents(context, limit = 50, offset = 0) {
  try {
    const result = await queryWithRetry(`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        v.latitude,
        v.longitude,
        (SELECT string_agg(c.name, ',') 
         FROM event_categories ec 
         JOIN categories c ON ec.category_id = c.id 
         WHERE ec.event_id = e.id) as categories
      FROM events e
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE e.status = 'published'
        AND (e.end_date IS NULL OR e.end_date >= CURRENT_DATE)
      ORDER BY e.start_date ASC, e.start_time ASC
      LIMIT $1 OFFSET $2
    `, [limit, offset]);
    
    return result.rows || [];
  } catch (error) {
    console.error('Error fetching events:', error);
    return [];
  }
}

// Get featured events
export async function getFeaturedEvents(context, limit = 6) {
  try {
    const result = await queryWithRetry(`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        (SELECT string_agg(c.name, ',') 
         FROM event_categories ec 
         JOIN categories c ON ec.category_id = c.id 
         WHERE ec.event_id = e.id) as categories
      FROM events e
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE e.status = 'published'
        AND e.is_featured = true
        AND (e.end_date IS NULL OR e.end_date >= CURRENT_DATE)
      ORDER BY e.start_date ASC
      LIMIT $1
    `, [limit]);
    
    return result.rows || [];
  } catch (error) {
    console.error('Error fetching featured events:', error);
    return [];
  }
}

// Get single event by slug
export async function getEventBySlug(context, slug) {
  try {
    const result = await queryWithRetry(`
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
        (SELECT string_agg(c.name, ',') 
         FROM event_categories ec 
         JOIN categories c ON ec.category_id = c.id 
         WHERE ec.event_id = e.id) as categories
      FROM events e
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE e.slug = $1
        AND e.status = 'published'
      LIMIT 1
    `, [slug]);
    
    return result.rows[0] || null;
  } catch (error) {
    console.error('Error fetching event by slug:', error);
    return null;
  }
}

// Get all categories
export async function getCategories(context) {
  try {
    const result = await queryWithRetry(`
      SELECT 
        c.*,
        COUNT(e.id) as event_count
      FROM categories c
      LEFT JOIN event_categories ec ON c.id = ec.category_id
      LEFT JOIN events e ON ec.event_id = e.id AND e.status = 'published'
      WHERE c.is_active = true
      GROUP BY c.id
      ORDER BY c.display_order ASC, c.name ASC
    `, []);
    
    return result.rows || [];
  } catch (error) {
    console.error('Error fetching categories:', error);
    return [];
  }
}

// Get category by slug
export async function getCategoryBySlug(context, slug) {
  try {
    const result = await queryWithRetry(`
      SELECT * FROM categories
      WHERE slug = $1 AND is_active = true
      LIMIT 1
    `, [slug]);
    
    return result.rows[0] || null;
  } catch (error) {
    console.error('Error fetching category by slug:', error);
    return null;
  }
}

// Get events by category
export async function getEventsByCategory(context, categorySlug, limit = 50) {
  try {
    const result = await queryWithRetry(`
      SELECT 
        e.*,
        v.name as venue_name_full,
        v.area,
        (SELECT string_agg(c2.name, ',') 
         FROM event_categories ec2 
         JOIN categories c2 ON ec2.category_id = c2.id 
         WHERE ec2.event_id = e.id) as categories
      FROM events e
      INNER JOIN event_categories ec ON e.id = ec.event_id
      INNER JOIN categories c ON ec.category_id = c.id
      LEFT JOIN venues v ON e.venue_id = v.id
      WHERE c.slug = $1
        AND e.status = 'published'
        AND (e.end_date IS NULL OR e.end_date >= CURRENT_DATE)
      ORDER BY e.start_date ASC, e.start_time ASC
      LIMIT $2
    `, [categorySlug, limit]);
    
    return result.rows || [];
  } catch (error) {
    console.error('Error fetching events by category:', error);
    return [];
  }
}

// Get all active sources
export async function getSources(context) {
  try {
    const result = await queryWithRetry(`
      SELECT * FROM sources
      WHERE is_active = true
      ORDER BY name ASC
    `, []);
    
    return result.rows || [];
  } catch (error) {
    console.error('Error fetching sources:', error);
    return [];
  }
}

// Health check endpoint
export async function healthCheck() {
  try {
    await queryWithRetry('SELECT 1', []);
    return { status: 'healthy', database: 'connected' };
  } catch (error) {
    return { status: 'unhealthy', database: 'disconnected', error: error.message };
  }
}
