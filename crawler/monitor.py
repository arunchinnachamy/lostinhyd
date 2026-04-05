#!/usr/bin/env python3
"""
Crawler monitor and reporter
Generates a summary of crawling results
"""

import asyncio
import asyncpg
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_URL = os.getenv('DATABASE_URL')
if not DB_URL:
    print("❌ Error: DATABASE_URL environment variable not set")
    sys.exit(1)

async def generate_report():
    """Generate a summary report of crawling activity"""
    conn = await asyncpg.connect(DB_URL)
    
    try:
        # Overall stats
        total_events = await conn.fetchval("SELECT COUNT(*) FROM crawler.raw_events")
        verified_events = await conn.fetchval(
            "SELECT COUNT(*) FROM crawler.raw_events WHERE processing_status = 'verified'")
        pending_events = await conn.fetchval(
            "SELECT COUNT(*) FROM crawler.raw_events WHERE processing_status = 'pending'")
        
        # Recent crawls (last 24 hours)
        recent_crawls = await conn.fetch("""
            SELECT 
                source_name,
                status,
                events_found,
                events_added,
                started_at,
                completed_at,
                error_message
            FROM crawler.crawl_batches
            WHERE started_at > NOW() - INTERVAL '24 hours'
            ORDER BY started_at DESC
        """)
        
        # Events by source
        source_stats = await conn.fetch("""
            SELECT 
                source_name,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE processing_status = 'verified') as verified,
                COUNT(*) FILTER (WHERE processing_status = 'cleaned') as cleaned,
                COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
                COUNT(*) FILTER (WHERE processing_status = 'rejected') as rejected,
                AVG(completeness_score)::int as avg_quality
            FROM crawler.raw_events
            GROUP BY source_name
            ORDER BY total DESC
        """)
        
        # High quality events (verified + high completeness)
        high_quality = await conn.fetch("""
            SELECT 
                source_name,
                raw_title,
                parsed_start_date,
                parsed_venue_name,
                completeness_score
            FROM crawler.raw_events
            WHERE processing_status = 'verified'
              AND completeness_score >= 90
              AND parsed_start_date >= CURRENT_DATE
            ORDER BY parsed_start_date
            LIMIT 10
        """)
        
        # Build report
        report = []
        report.append("=" * 60)
        report.append("📊 LOST IN HYDERABAD - CRAWLER REPORT")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        
        report.append("\n📈 OVERALL STATISTICS")
        report.append(f"  Total Events: {total_events}")
        report.append(f"  ✅ Verified: {verified_events}")
        report.append(f"  ⏳ Pending: {pending_events}")
        report.append(f"  📦 Success Rate: {(verified_events/max(total_events,1)*100):.1f}%")
        
        report.append("\n📊 EVENTS BY SOURCE")
        report.append(f"  {'Source':<15} {'Total':>8} {'Verified':>10} {'Quality':>10}")
        report.append(f"  {'-'*15} {'-'*8} {'-'*10} {'-'*10}")
        for row in source_stats:
            report.append(f"  {row['source_name']:<15} {row['total']:>8} {row['verified']:>10} {row['avg_quality']:>9}%")
        
        if recent_crawls:
            report.append("\n🔄 RECENT CRAWLS (Last 24 Hours)")
            for row in recent_crawls:
                status_icon = "✅" if row['status'] == 'completed' else "❌"
                report.append(f"  {status_icon} {row['source_name']:<15} | Found: {row['events_found']:>3} | Added: {row['events_added']:>3} | {row['started_at'].strftime('%H:%M')}")
                if row['error_message']:
                    report.append(f"     ⚠️  Error: {row['error_message'][:50]}")
        else:
            report.append("\n⚠️  No crawls in last 24 hours")
        
        if high_quality:
            report.append("\n🎯 UPCOMING VERIFIED EVENTS")
            for row in high_quality:
                date_str = row['parsed_start_date'].strftime('%b %d') if row['parsed_start_date'] else 'TBA'
                report.append(f"  📅 {date_str} | {row['raw_title'][:40]:<40} | {row['source_name']}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)
        
    finally:
        await conn.close()


if __name__ == '__main__':
    report = asyncio.run(generate_report())
    print(report)
