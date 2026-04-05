-- Migration 002: Additional indexes for admin dashboard queries

SET search_path TO lostinhyd, public;

-- Crawl logs are queried by started_at and status frequently
CREATE INDEX IF NOT EXISTS idx_crawl_logs_started ON crawl_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_status ON crawl_logs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_logs_source ON crawl_logs(source_id);
