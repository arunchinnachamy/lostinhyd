-- Migration 001: Initial schema for Lost in Hyd
-- Schema: lostinhyd
-- Database: toolradar (OVH Managed PostgreSQL)

CREATE SCHEMA IF NOT EXISTS lostinhyd;
SET search_path TO lostinhyd, public;

-- Sources: websites/platforms we crawl
CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(512),
    source_type VARCHAR(50) CHECK (source_type IN ('website', 'api', 'rss', 'manual', 'social')),
    is_active BOOLEAN DEFAULT true,
    crawl_frequency VARCHAR(20) DEFAULT 'daily',
    last_crawled TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Venues
CREATE TABLE IF NOT EXISTS venues (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100) DEFAULT 'Hyderabad',
    area VARCHAR(100),
    state VARCHAR(50) DEFAULT 'Telangana',
    country VARCHAR(50) DEFAULT 'India',
    pincode VARCHAR(10),
    latitude NUMERIC,
    longitude NUMERIC,
    phone VARCHAR(20),
    website VARCHAR(512),
    google_maps_url VARCHAR(512),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INTEGER REFERENCES categories(id),
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) NOT NULL UNIQUE,
    description TEXT,
    content TEXT,
    start_date DATE,
    start_time TIME,
    end_date DATE,
    end_time TIME,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    is_recurring BOOLEAN DEFAULT false,
    recurrence_pattern VARCHAR(100),
    venue_id INTEGER REFERENCES venues(id) ON DELETE SET NULL,
    venue_name VARCHAR(255),
    venue_address TEXT,
    is_online BOOLEAN DEFAULT false,
    online_url VARCHAR(512),
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    source_url VARCHAR(512),
    source_event_id VARCHAR(255),
    image_url VARCHAR(512),
    gallery_urls TEXT[],
    is_free BOOLEAN DEFAULT false,
    price_min NUMERIC,
    price_max NUMERIC,
    currency VARCHAR(3) DEFAULT 'INR',
    ticket_url VARCHAR(512),
    age_limit VARCHAR(20),
    organizer VARCHAR(255),
    tags TEXT[],
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived', 'rejected')),
    is_featured BOOLEAN DEFAULT false,
    meta_title VARCHAR(255),
    meta_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event-Category junction
CREATE TABLE IF NOT EXISTS event_categories (
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT false,
    PRIMARY KEY (event_id, category_id)
);

-- Crawl logs
CREATE TABLE IF NOT EXISTS crawl_logs (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    crawl_type VARCHAR(50) DEFAULT 'full',
    status VARCHAR(20) DEFAULT 'running',
    events_found INTEGER DEFAULT 0,
    events_added INTEGER DEFAULT 0,
    events_updated INTEGER DEFAULT 0,
    events_skipped INTEGER DEFAULT 0,
    errors TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_events_status ON events(status);
CREATE INDEX IF NOT EXISTS idx_events_start_date ON events(start_date);
CREATE INDEX IF NOT EXISTS idx_events_slug ON events(slug);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_id);
CREATE INDEX IF NOT EXISTS idx_events_venue ON events(venue_id);
CREATE INDEX IF NOT EXISTS idx_venues_area ON venues(area);
CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories(slug);
