#!/usr/bin/env python3
"""
Script to add retry_count column to existing submissions table
"""

import os
from dotenv import load_dotenv
from flask import Flask
from models import db, Submission

# Load environment variables
load_dotenv()

def add_retry_count_column():
    """Add retry_count column to submissions table if it doesn't exist."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        try:
            # Check if retry_count column exists
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('submissions')]
            
            if 'retry_count' not in columns:
                print("Adding retry_count column to submissions table...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE submissions ADD COLUMN retry_count INTEGER DEFAULT 0'))
                    conn.commit()
                print("✅ retry_count column added successfully!")
            else:
                print("✅ retry_count column already exists")
            
            # Update existing failed submissions to have retry_count = 0
            failed_submissions = Submission.query.filter_by(status='failed').all()
            for submission in failed_submissions:
                if submission.retry_count is None:
                    submission.retry_count = 0
            
            db.session.commit()
            print(f"✅ Updated {len(failed_submissions)} failed submissions with retry_count")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
        
        return True

if __name__ == "__main__":
    print("🔄 Adding retry_count column to database...")
    if add_retry_count_column():
        print("🎉 Database migration completed successfully!")
    else:
        print("💥 Database migration failed!")
