#!/usr/bin/env python3
"""
Migration script to add temperature and max_tokens columns to grading_jobs and job_batches tables.
This script should be run once to update the database schema.
"""

import os
import sys
from dotenv import load_dotenv

# Add the current directory to Python path to import the models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

def run_migration():
    """Run the database migration to add model parameter fields."""

    # Import here to avoid circular imports and ensure environment is loaded
    from flask import Flask
    from models import db

    # Create Flask app with same configuration as main app
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize database
    db.init_app(app)

    with app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect, text

            inspector = inspect(db.engine)

            # Check grading_jobs table
            grading_jobs_columns = [col['name'] for col in inspector.get_columns('grading_jobs')]

            # Add temperature and max_tokens to grading_jobs if they don't exist
            if 'temperature' not in grading_jobs_columns:
                print("Adding temperature column to grading_jobs table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE grading_jobs ADD COLUMN temperature FLOAT DEFAULT 0.3"))
                    conn.commit()
                print("✓ Added temperature column to grading_jobs")

            if 'max_tokens' not in grading_jobs_columns:
                print("Adding max_tokens column to grading_jobs table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE grading_jobs ADD COLUMN max_tokens INTEGER DEFAULT 2000"))
                    conn.commit()
                print("✓ Added max_tokens column to grading_jobs")

            # Check job_batches table
            job_batches_columns = [col['name'] for col in inspector.get_columns('job_batches')]

            # Add temperature and max_tokens to job_batches if they don't exist
            if 'temperature' not in job_batches_columns:
                print("Adding temperature column to job_batches table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE job_batches ADD COLUMN temperature FLOAT DEFAULT 0.3"))
                    conn.commit()
                print("✓ Added temperature column to job_batches")

            if 'max_tokens' not in job_batches_columns:
                print("Adding max_tokens column to job_batches table...")
                with db.engine.connect() as conn:
                    conn.execute(text("ALTER TABLE job_batches ADD COLUMN max_tokens INTEGER DEFAULT 2000"))
                    conn.commit()
                print("✓ Added max_tokens column to job_batches")

            print("\n✅ Migration completed successfully!")
            print("The database now supports configurable temperature and max_tokens parameters.")

        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            print("You may need to run this migration manually or check your database permissions.")
            return False

    return True

if __name__ == "__main__":
    print("🔄 Starting database migration for model parameters...")
    success = run_migration()
    if success:
        print("\n🎉 Migration completed! You can now use configurable model parameters.")
    else:
        print("\n💥 Migration failed. Please check the error messages above.")
        sys.exit(1)
