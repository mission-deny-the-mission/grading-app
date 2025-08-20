#!/usr/bin/env python3
"""
Database migration script for multi-model comparison feature.
This script adds the new GradeResult table and updates existing tables.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def migrate_database():
    """Run database migrations for multi-model comparison feature."""
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    
    print(f"Connecting to database: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if grade_results table already exists
            try:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='grade_results'"))
                if result.fetchone():
                    print("✓ GradeResult table already exists")
                else:
                    print("Creating GradeResult table...")
                    
                    # Create grade_results table
                    conn.execute(text("""
                        CREATE TABLE grade_results (
                            id VARCHAR(36) PRIMARY KEY,
                            created_at DATETIME,
                            grade TEXT NOT NULL,
                            provider VARCHAR(50) NOT NULL,
                            model VARCHAR(100) NOT NULL,
                            status VARCHAR(50) DEFAULT 'completed',
                            error_message TEXT,
                            grade_metadata JSON,
                            submission_id VARCHAR(36) NOT NULL,
                            FOREIGN KEY (submission_id) REFERENCES submissions (id)
                        )
                    """))
                    print("✓ GradeResult table created successfully")
                    
            except OperationalError as e:
                print(f"Error checking/creating grade_results table: {e}")
                return False
            
            # Check if models_to_compare column exists in grading_jobs table
            try:
                result = conn.execute(text("PRAGMA table_info(grading_jobs)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'models_to_compare' not in columns:
                    print("Adding models_to_compare column to grading_jobs table...")
                    # SQLite doesn't support JSON type, use TEXT instead
                    conn.execute(text("ALTER TABLE grading_jobs ADD COLUMN models_to_compare TEXT"))
                    print("✓ models_to_compare column added successfully")
                else:
                    print("✓ models_to_compare column already exists")
                    
            except OperationalError as e:
                print(f"Error checking/adding models_to_compare column: {e}")
                return False
            
            # Commit changes
            conn.commit()
            print("✓ Database migration completed successfully")
            return True
            
    except Exception as e:
        print(f"Error during migration: {e}")
        return False

if __name__ == "__main__":
    print("Starting database migration for multi-model comparison feature...")
    
    if migrate_database():
        print("\nMigration completed successfully!")
        print("You can now use the multi-model comparison feature.")
    else:
        print("\nMigration failed!")
        sys.exit(1)
