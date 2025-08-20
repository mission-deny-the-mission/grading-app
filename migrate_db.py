#!/usr/bin/env python3
"""
Database migration script for adding marking scheme support.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def migrate_database():
    """Run database migrations."""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    
    # Create engine
    engine = create_engine(database_url)
    
    print("Starting database migration...")
    
    try:
        with engine.connect() as conn:
            # Check if marking_schemes table exists
            result = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='marking_schemes'
            """))
            
            if not result.fetchone():
                print("Creating marking_schemes table...")
                conn.execute(text("""
                    CREATE TABLE marking_schemes (
                        id VARCHAR(36) PRIMARY KEY,
                        created_at DATETIME,
                        updated_at DATETIME,
                        name VARCHAR(255) NOT NULL,
                        description TEXT,
                        filename VARCHAR(255) NOT NULL,
                        original_filename VARCHAR(255) NOT NULL,
                        file_size INTEGER,
                        file_type VARCHAR(10),
                        content TEXT
                    )
                """))
                print("✓ marking_schemes table created")
            else:
                print("✓ marking_schemes table already exists")
            
            # Check if marking_scheme_id column exists in grading_jobs table
            result = conn.execute(text("""
                PRAGMA table_info(grading_jobs)
            """))
            
            columns = [row[1] for row in result.fetchall()]
            
            if 'marking_scheme_id' not in columns:
                print("Adding marking_scheme_id column to grading_jobs table...")
                conn.execute(text("""
                    ALTER TABLE grading_jobs 
                    ADD COLUMN marking_scheme_id VARCHAR(36) 
                    REFERENCES marking_schemes(id)
                """))
                print("✓ marking_scheme_id column added")
            else:
                print("✓ marking_scheme_id column already exists")
            
            # Commit changes
            conn.commit()
            
        print("Database migration completed successfully!")
        
    except OperationalError as e:
        print(f"Database migration failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error during migration: {e}")
        sys.exit(1)

if __name__ == '__main__':
    migrate_database()
