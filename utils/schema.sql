-- PostgreSQL Schema for Lost in Hyd Event Aggregation System

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Main events table for crawled events
CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    event_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    location VARCHAR(500),
    area VARCHAR(200),
    venue VARCHAR(500),
    price VARCHAR(200),
    currency VARCHAR(10) DEFAULT 'INR',
    link TEXT,
    image_url TEXT,
    
    -- Source tracking
    source VARCHAR(200) NOT NULL,  -- e.g., 'bookmyshow', 'insider', 'venue_website'
    source_url TEXT,
    source_id VARCHAR(500),  -- ID from the source system
    
    -- Categorization
    category VARCHAR(100),  -- food, music, art, sports, etc.
    tags TEXT[],  -- Array of tags
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'draft',  -- draft, published, rejected, expired
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    crawled_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Unique constraint on source + source_id to prevent duplicates
    CONSTRAINT unique_source_event UNIQUE (source, source_id)
);

-- Create indexes for common queries
CREATE INDEX idx_events_date ON events(event_date);
CREATE INDEX idx_events_area ON events(area);
CREATE INDEX idx_events_category ON events(category);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_source ON events(source);
CREATE INDEX idx_events_tags ON events USING GIN(tags);

-- Table for event sources (websites/platforms we crawl)
CREATE TABLE IF NOT EXISTS event_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    crawler_type VARCHAR(100),  -- e.g., 'rss', 'api', 'scrape', 'manual'
    crawl_frequency VARCHAR(50) DEFAULT 'daily',  -- hourly, daily, weekly
    last_crawled TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    
    -- Rate limiting and config
    rate_limit_seconds INTEGER DEFAULT 60,
    config JSONB,  -- Source-specific configuration
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Crawl logs for tracking
CREATE TABLE IF NOT EXISTS crawl_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID REFERENCES event_sources(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    events_found INTEGER DEFAULT 0,
    events_new INTEGER DEFAULT 0,
    events_updated INTEGER DEFAULT 0,
    events_failed INTEGER DEFAULT 0,
    status VARCHAR(50),  -- running, success, failed
    error_message TEXT,
    log_details JSONB
);

-- Places table for aggregating venue/place information
CREATE TABLE IF NOT EXISTS places (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(500) NOT NULL,
    description TEXT,
    area VARCHAR(200),
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    map_link TEXT,
    
    -- Categorization
    category VARCHAR(100),  -- cafe, restaurant, attraction, park, market, museum
    tags TEXT[],
    
    -- Images
    hero_image_url TEXT,
    image_urls TEXT[],
    
    -- Practical info
    best_time VARCHAR(500),
    must_try VARCHAR(500),
    price_range VARCHAR(50),  -- budget, moderate, expensive
    timings JSONB,  -- e.g., {"mon": "9AM-10PM", "tue": "9AM-10PM"}
    contact_info JSONB,
    
    -- Source tracking
    source VARCHAR(200),
    source_url TEXT,
    
    -- Status
    featured BOOLEAN DEFAULT false,
    status VARCHAR(50) DEFAULT 'draft',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_places_area ON places(area);
CREATE INDEX idx_places_category ON places(category);
CREATE INDEX idx_places_featured ON places(featured) WHERE featured = true;

-- Newsletter editions table
CREATE TABLE IF NOT EXISTS newsletters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    edition_number INTEGER UNIQUE,
    title VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE,
    description TEXT,
    content TEXT,
    
    -- Publishing
    pub_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, scheduled, published
    
    -- Metadata
    category VARCHAR(100),
    area VARCHAR(200),
    keywords TEXT[],
    featured BOOLEAN DEFAULT false,
    hero_image_url TEXT,
    
    -- Stats
    views INTEGER DEFAULT 0,
    subscribers_count INTEGER,
    
    -- Related content
    featured_event_ids UUID[],
    featured_place_ids UUID[],
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_newsletters_pub_date ON newsletters(pub_date);
CREATE INDEX idx_newsletters_status ON newsletters(status);

-- Junction table for newsletter events
CREATE TABLE IF NOT EXISTS newsletter_events (
    newsletter_id UUID REFERENCES newsletters(id) ON DELETE CASCADE,
    event_id UUID REFERENCES events(id) ON DELETE CASCADE,
    section VARCHAR(100),  -- e.g., 'featured', 'mentions'
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (newsletter_id, event_id)
);

-- Junction table for newsletter places
CREATE TABLE IF NOT EXISTS newsletter_places (
    newsletter_id UUID REFERENCES newsletters(id) ON DELETE CASCADE,
    place_id UUID REFERENCES places(id) ON DELETE CASCADE,
    section VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    PRIMARY KEY (newsletter_id, place_id)
);

-- Function to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for auto-updating updated_at
CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_places_updated_at BEFORE UPDATE ON places
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_newsletters_updated_at BEFORE UPDATE ON newsletters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some default event sources
INSERT INTO event_sources (name, base_url, crawler_type, crawl_frequency, is_active, config)
VALUES 
    ('bookmyshow', 'https://in.bookmyshow.com/explore/home/hyderabad', 'scrape', 'daily', true, 
     '{"city": "hyderabad", "category": "events"}'),
    ('insider', 'https://insider.in/hyderabad', 'scrape', 'daily', true,
     '{"city": "hyderabad"}'),
    ('allevents', 'https://allevents.in/hyderabad', 'scrape', 'daily', true,
     '{"city": "hyderabad"}'),
    ('facebook_events', 'https://www.facebook.com/events/search', 'api', 'daily', false,
     '{"city": "hyderabad", "radius": 25}'),
    ('venue_manual', 'manual', 'manual', 'weekly', true,
     '{"note": "Manually added events from venues"}')
ON CONFLICT (name) DO NOTHING;

-- Views for easier querying
CREATE OR REPLACE VIEW upcoming_events AS
SELECT * FROM events 
WHERE event_date >= NOW() 
AND status IN ('draft', 'published')
ORDER BY event_date ASC;

CREATE OR REPLACE VIEW events_by_area AS
SELECT area, COUNT(*) as event_count
FROM events 
WHERE event_date >= NOW()
AND area IS NOT NULL
GROUP BY area
ORDER BY event_count DESC;
