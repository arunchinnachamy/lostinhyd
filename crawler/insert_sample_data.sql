-- Insert sample test data for crawler testing

-- Create test batch (valid UUID)
INSERT INTO crawler.crawl_batches (id, source_name, status, events_found)
VALUES ('550e8400-e29b-41d4-a716-446655440000', 'test', 'completed', 5)
ON CONFLICT (id) DO NOTHING;

-- Insert sample events
INSERT INTO crawler.raw_events (
    source_name, source_url, source_id, crawl_batch_id,
    raw_title, raw_description, raw_date_text, raw_time_text,
    raw_location_text, raw_price_text, raw_image_urls, raw_category_text,
    raw_organizer, crawl_status, http_status, processing_status
) VALUES 
(
    'bookmyshow',
    'https://in.bookmyshow.com/events/comedy-night-hyderabad/ET00001',
    'bms-12345',
    '550e8400-e29b-41d4-a716-446655440000',
    'Comedy Night with Kanan Gill - Live in Hyderabad',
    'Join Kanan Gill for an evening of laughter and comedy at The Moonshine Project. Get ready for hilarious takes on life, relationships, and everything in between.',
    '15 April 2026',
    '7:30 PM',
    'The Moonshine Project, Road No 12, Banjara Hills, Hyderabad',
    '₹499 - ₹1,499',
    ARRAY['https://example.com/image1.jpg'],
    'Comedy',
    'BookMyShow',
    'success',
    200,
    'pending'
),
(
    'eventshigh',
    'https://www.eventshigh.com/detail/hyderabad/evt-123',
    'eh-67890',
    '550e8400-e29b-41d4-a716-446655440000',
    '  Music Festival 2026 - Indie Rock Night!! ',
    '<p>Join us for an amazing night of <b>indie rock</b> music featuring top bands from across India.</p>',
    '20 Apr 2026',
    '6:00 pm',
    'Gachibowli Stadium, Hyderabad, Telangana',
    'Free Entry',
    ARRAY[]::TEXT[],
    'Music',
    NULL,
    'success',
    200,
    'pending'
),
(
    'meetup',
    'https://www.meetup.com/hyderabad-tech/events/abc123',
    'meetup-xyz',
    '550e8400-e29b-41d4-a716-446655440000',
    'Hyderabad Tech Startup Networking Meetup',
    'Network with fellow tech entrepreneurs and startup founders. Great opportunity to connect with investors and mentors in the Hyderabad ecosystem.',
    'Tomorrow',
    '18:30',
    'WeWork Hitech City, Kondapur, Hyderabad',
    '',
    ARRAY['https://example.com/meetup.jpg'],
    'Networking',
    'Hyderabad Tech Meetup Group',
    'success',
    200,
    'pending'
),
(
    'allevents',
    'https://allevents.in/hyderabad/food-festival',
    'ae-99999',
    '550e8400-e29b-41d4-a716-446655440000',
    'Hyderabad Food & Wine Festival 2026',
    'Experience the finest culinary delights from top chefs across India. Wine tasting, food stalls, live music, and more.',
    '25-27 April 2026',
    '12:00 PM onwards',
    'Park Hyatt Hyderabad, Road No 2, Banjara Hills',
    '₹2,500 onwards',
    ARRAY['https://example.com/food.jpg', 'https://example.com/wine.jpg'],
    'Food & Drink',
    'Hyderabad Food Council',
    'success',
    200,
    'pending'
),
(
    'townscript',
    'https://www.townscript.com/in/hyderabad/marathon',
    'ts-77777',
    '550e8400-e29b-41d4-a716-446655440000',
    'Hyderabad City Marathon 2026',
    'Join thousands of runners for the annual Hyderabad marathon. Categories: Full Marathon, Half Marathon, 10K, 5K Fun Run.',
    '10 May 2026',
    '5:00 AM',
    'Hussain Sagar Lake, Necklace Road, Hyderabad',
    '₹800 - ₹2,000',
    ARRAY['https://example.com/marathon.jpg'],
    'Sports',
    'Hyderabad Runners Club',
    'success',
    200,
    'pending'
)
ON CONFLICT (source_name, source_id) DO UPDATE SET
    raw_title = EXCLUDED.raw_title,
    updated_at = CURRENT_TIMESTAMP;

-- Verify insertion
SELECT 
    source_name, 
    SUBSTRING(raw_title, 1, 40) as title,
    raw_date_text,
    processing_status
FROM crawler.raw_events
WHERE crawl_batch_id = '550e8400-e29b-41d4-a716-446655440000'
ORDER BY id;
