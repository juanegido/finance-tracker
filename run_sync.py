#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cron-friendly wrapper for finance tracker sync
Includes logging and error handling for automated runs
"""

import sys
import os
import logging
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging():
    """Set up logging for cron runs"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, f"finance_sync_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

def main():
    """Main cron runner function"""
    logger = setup_logging()
    
    try:
        logger.info("=== Starting Finance Tracker Sync ===")
        
        # Import and run the main finance tracker
        from finance_tracker_sheets import main as finance_main
        
        finance_main()
        
        logger.info("=== Finance Tracker Sync Completed Successfully ===")
        return 0
        
    except Exception as e:
        logger.error(f"=== Finance Tracker Sync Failed: {e} ===")
        logger.exception("Full error details:")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
