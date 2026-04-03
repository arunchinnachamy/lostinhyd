-- Create crawler schema
CREATE SCHEMA IF NOT EXISTS crawler;

-- Raw events table (stores crawled data as-is)
CREATE TABLE IF NOT EXISTS crawler.raw_events (
    id SERIAL PRIMARY KEY,
    
    -- Source tracking
    source_name VARCHAR(50) NOT NULL,
    source_url TEXT NOT NULL,
    source_id VARCHAR(255),
    crawl_batch_id UUID,
    
    -- Raw extracted data (as-is from source)
    raw_title TEXT NOT NULL,
    raw_description TEXT,
    raw_date_text TEXT,
    raw_time_text TEXT,
    raw_location_text TEXT,
    raw_price_text TEXT,
    raw_image_urls TEXT[],
    raw_category_text TEXT,
    raw_organizer TEXT,
    raw_contact_info TEXT,
    
    -- Structured data (parsed but not cleaned)
    parsed_start_date DATE,
    parsed_start_time TIME,
    parsed_end_date DATE,
    parsed_end_time TIME,
    parsed_venue_name TEXT,
    parsed_address TEXT,
    parsed_city TEXT DEFAULT 'Hyderabad',
    parsed_latitude DECIMAL(10,8),
    parsed_longitude DECIMAL(11,8),
    parsed_is_free BOOLEAN,
    parsed_price_min DECIMAL(10,2),
    parsed_price_max DECIMAL(10,2),
    parsed_currency VARCHAR(3) DEFAULT 'INR',
    parsed_age_limit TEXT,
    
    -- Crawl metadata
    crawl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crawl_status VARCHAR(20) DEFAULT 'success',
    crawl_error_message TEXT,
    http_status INTEGER,
    page_html_hash VARCHAR(64),
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'pending',
    processing_notes TEXT,
    duplicate_of_id INTEGER REFERENCES crawler.raw_events(id),
    
    -- Data quality scores
    completeness_score INTEGER,
    accuracy_score INTEGER,
    confidence_score INTEGER,
    
    -- Verification
    verified_by VARCHAR(50),
    verified_at TIMESTAMP,
    
    -- Migration tracking
    migrated_to_d1 BOOLEAN DEFAULT FALSE,
    migrated_at TIMESTAMP,
    d1_event_id INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint per source event
    UNIQUE(source_name, source_id)
);

-- Crawl batches table
CREATE TABLE IF NOT EXISTS crawler.crawl_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    source_name VARCHAR(50),
    events_found INTEGER DEFAULT 0,
    events_added INTEGER DEFAULT 0,
    events_updated INTEGER DEFAULT 0,
    events_rejected INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',
    logs TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Source configurations table
CREATE TABLE IF NOT EXISTS crawler.source_configs (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(50) UNIQUE NOT NULL,
    source_url TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    
    -- Crawl settings
    crawl_frequency VARCHAR(20) DEFAULT 'daily',
    crawl_hour INTEGER DEFAULT 6,
    rate_limit_requests INTEGER DEFAULT 10,
    request_timeout INTEGER DEFAULT 30,
    retry_attempts INTEGER DEFAULT 3,
    
    -- Configs stored as JSONB
    selector_config JSONB DEFAULT '{}',
    api_config JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_crawled_at TIMESTAMP,
    last_error_at TIMESTAMP,
    last_error_message TEXT,
    total_crawls INTEGER DEFAULT 0,
    total_events_found INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data quality rules table
CREATE TABLE IF NOT EXISTS crawler.data_quality_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    field_name VARCHAR(100) NOT NULL,
    condition TEXT,
    error_message TEXT,
    severity VARCHAR(20) DEFAULT 'warning',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes
CREATE INDEX idx_raw_events_source ON crawler.raw_events(source_name);
CREATE INDEX idx_raw_events_status ON crawler.raw_events(processing_status);
CREATE INDEX idx_raw_events_migrated ON crawler.raw_events(migrated_to_d1);
CREATE INDEX idx_raw_events_date ON crawler.raw_events(parsed_start_date);
CREATE INDEX idx_raw_events_crawl_time ON crawler.raw_events(crawl_timestamp);
CREATE INDEX idx_raw_events_batch ON crawler.raw_events(crawl_batch_id);
CREATE INDEX idx_raw_events_duplicate ON crawler.raw_events(duplicate_of_id);

-- Insert source configs
INSERT INTO crawler.source_configs (source_name, source_url, source_type, crawl_frequency, rate_limit_requests) VALUES
('bookmyshow', 'https://in.bookmyshow.com/explore/events-hyderabad', 'html_scrape', 'daily', 20),
('eventshigh', 'https://www.eventshigh.com/hyderabad', 'html_scrape', 'daily', 15),
('meetup', 'https://www.meetup.com/find/in--hyderabad/', 'api', 'daily', 30),
('allevents', 'https://allevents.in/hyderabad', 'html_scrape', 'daily', 15),
('townscript', 'https://www.townscript.com/in/hyderabad', 'html_scrape', 'daily', 10),
('fullhyderabad', 'https://events.fullhyderabad.com', 'html_scrape', 'daily', 10)
ON CONFLICT (source_name) DO NOTHING;

-- Insert quality rules
INSERT INTO crawler.data_quality_rules (rule_name, rule_type, field_name, condition, error_message, severity) VALUES
('title_required', 'required', 'raw_title', NULL, 'Event title is required', 'error'),
('title_length', 'format', 'raw_title', 'LENGTH(raw_title) >= 5', 'Title must be at least 5 characters', 'warning'),
('date_required', 'required', 'raw_date_text', NULL, 'Event date is required', 'warning'),
('future_date', 'custom', 'parsed_start_date', 'parsed_start_date >= CURRENT_DATE', 'Event date is in the past', 'warning'),
('price_positive', 'range', 'parsed_price_min', 'parsed_price_min >= 0', 'Price cannot be negative', 'error'),
('venue_required', 'required', 'raw_location_text', NULL, 'Venue information is missing', 'warning'),
('description_length', 'format', 'raw_description', 'LENGTH(raw_description) >= 20', 'Description is too short', 'info')
ON CONFLICT DO NOTHING;

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION crawler.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_raw_events_updated_at ON crawler.raw_events;
CREATE TRIGGER update_raw_events_updated_at BEFORE UPDATE ON crawler.raw_events
    FOR EACH ROW EXECUTE FUNCTION crawler.update_updated_at_column();

DROP TRIGGER IF EXISTS update_source_configs_updated_at ON crawler.source_configs;
CREATE TRIGGER update_source_configs_updated_at BEFORE UPDATE ON crawler.source_configs
    FOR EACH ROW EXECUTE FUNCTION crawler.update_updated_at_column();
