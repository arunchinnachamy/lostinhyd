#!/usr/bin/env python3
"""
Automated crawler runner - runs crawlers, cleans data, generates report
This is the main entry point for scheduled crawling
"""

import asyncio
import subprocess
import sys
import os
from datetime import datetime

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"🔄 {description}")
    print(f"{'='*60}")
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout[-500:])  # Last 500 chars
        return True
    else:
        print(f"❌ {description} failed")
        print(f"Error: {result.stderr[:500]}")
        return False

async def generate_report():
    """Generate and display report"""
    from monitor import generate_report
    report = await generate_report()
    print("\n" + report)
    return report

def main():
    """Main automation workflow"""
    start_time = datetime.now()
    
    print("="*60)
    print("🤖 LOST IN HYDERABAD - AUTOMATED CRAWLER")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Step 1: Run all crawlers
    crawl_success = run_command(
        "python3 run_crawler.py --all",
        "Running all crawlers"
    )
    
    # Step 2: Clean the data
    clean_success = run_command(
        "python3 clean_data.py --all",
        "Cleaning crawled data"
    )
    
    # Step 3: Generate report
    print("\n" + "="*60)
    print("📊 GENERATING REPORT")
    print("="*60)
    
    try:
        report = asyncio.run(generate_report())
        
        # Save report to file
        report_file = f"reports/crawler_report_{start_time.strftime('%Y%m%d_%H%M%S')}.txt"
        os.makedirs("reports", exist_ok=True)
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"\n📄 Report saved to: {report_file}")
        
    except Exception as e:
        print(f"⚠️  Error generating report: {e}")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "="*60)
    print("✅ AUTOMATION COMPLETE")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Crawl: {'✅' if crawl_success else '❌'}")
    print(f"Clean: {'✅' if clean_success else '❌'}")
    print("="*60)
    
    return 0 if (crawl_success and clean_success) else 1

if __name__ == '__main__':
    sys.exit(main())
