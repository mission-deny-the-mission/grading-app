#!/usr/bin/env python3
"""
Database migration script for enhanced batch system.
This script adds new columns and tables for the comprehensive batch functionality.
"""

import os
import sys
from flask import Flask
from models import db, BatchTemplate, JobBatch
from sqlalchemy import text

def create_app():
    """Create Flask app for migration."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def migrate_batch_enhancements():
    """Apply batch enhancement migrations."""
    app = create_app()
    
    with app.app_context():
        print("Starting batch enhancements migration...")
        
        try:
            # Create new BatchTemplate table
            print("Creating batch_templates table...")
            db.create_all()
            
            # Add new columns to job_batches table
            print("Adding new columns to job_batches table...")
            
            # Check if columns already exist to avoid errors
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('job_batches')]
            
            migrations = [
                ('updated_at', 'DATETIME'),
                ('priority', 'INTEGER DEFAULT 5'),
                ('tags', 'JSON'),
                ('models_to_compare', 'JSON'),
                ('batch_settings', 'JSON'),
                ('auto_assign_jobs', 'BOOLEAN DEFAULT 0'),
                ('total_jobs', 'INTEGER DEFAULT 0'),
                ('completed_jobs', 'INTEGER DEFAULT 0'),
                ('failed_jobs', 'INTEGER DEFAULT 0'),
                ('deadline', 'DATETIME'),
                ('started_at', 'DATETIME'),
                ('completed_at', 'DATETIME'),
                ('estimated_completion', 'DATETIME'),
                ('template_id', 'VARCHAR(36)'),
                ('created_by', 'VARCHAR(100)'),
                ('shared_with', 'JSON'),
                ('saved_prompt_id', 'VARCHAR(36)'),
                ('saved_marking_scheme_id', 'VARCHAR(36)')
            ]
            
            for column_name, column_type in migrations:
                if column_name not in existing_columns:
                    try:
                        # SQLite syntax
                        if 'sqlite' in str(db.engine.url):
                            sql = f"ALTER TABLE job_batches ADD COLUMN {column_name} {column_type}"
                        else:
                            # PostgreSQL syntax
                            sql = f"ALTER TABLE job_batches ADD COLUMN {column_name} {column_type}"
                        
                        db.session.execute(text(sql))
                        print(f"Added column: {column_name}")
                    except Exception as e:
                        print(f"Warning: Could not add column {column_name}: {e}")
            
            # Update status column to support new statuses
            print("Updating batch status values...")
            try:
                # Update existing 'pending' status to 'draft' for consistency
                db.session.execute(text("UPDATE job_batches SET status = 'draft' WHERE status = 'pending'"))
                print("Updated status values")
            except Exception as e:
                print(f"Warning: Could not update status values: {e}")
            
            # Add foreign key constraints if using PostgreSQL
            if 'postgresql' in str(db.engine.url):
                try:
                    print("Adding foreign key constraints...")
                    db.session.execute(text("""
                        ALTER TABLE job_batches 
                        ADD CONSTRAINT fk_batch_template 
                        FOREIGN KEY (template_id) REFERENCES batch_templates(id)
                    """))
                    
                    db.session.execute(text("""
                        ALTER TABLE job_batches 
                        ADD CONSTRAINT fk_batch_saved_prompt 
                        FOREIGN KEY (saved_prompt_id) REFERENCES saved_prompts(id)
                    """))
                    
                    db.session.execute(text("""
                        ALTER TABLE job_batches 
                        ADD CONSTRAINT fk_batch_saved_marking_scheme 
                        FOREIGN KEY (saved_marking_scheme_id) REFERENCES saved_marking_schemes(id)
                    """))
                    print("Added foreign key constraints")
                except Exception as e:
                    print(f"Warning: Could not add foreign key constraints: {e}")
            
            # Commit all changes
            db.session.commit()
            print("Migration completed successfully!")
            
            # Create some default batch templates
            print("Creating default batch templates...")
            create_default_templates()
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            return False
        
        return True

def create_default_templates():
    """Create some default batch templates."""
    templates = [
        {
            'name': 'Academic Essay Grading',
            'description': 'Standard template for grading academic essays and papers',
            'category': 'academic',
            'default_settings': {
                'provider': 'openrouter',
                'model': 'anthropic/claude-3-5-sonnet-20241022',
                'temperature': 0.3,
                'max_tokens': 2000
            },
            'job_structure': {
                'auto_naming': True,
                'naming_pattern': 'Essay - {filename}',
                'priority': 5
            },
            'processing_rules': {
                'auto_start': False,
                'retry_failed': True,
                'max_retries': 3
            },
            'is_public': True
        },
        {
            'name': 'Business Report Review',
            'description': 'Template for reviewing business reports and proposals',
            'category': 'business',
            'default_settings': {
                'provider': 'openrouter',
                'model': 'anthropic/claude-3-5-sonnet-20241022',
                'temperature': 0.2,
                'max_tokens': 3000
            },
            'job_structure': {
                'auto_naming': True,
                'naming_pattern': 'Report - {filename}',
                'priority': 7
            },
            'processing_rules': {
                'auto_start': False,
                'retry_failed': True,
                'max_retries': 2
            },
            'is_public': True
        },
        {
            'name': 'Research Paper Analysis',
            'description': 'Comprehensive template for analyzing research papers',
            'category': 'research',
            'default_settings': {
                'provider': 'openrouter',
                'model': 'anthropic/claude-3-5-sonnet-20241022',
                'temperature': 0.1,
                'max_tokens': 4000
            },
            'job_structure': {
                'auto_naming': True,
                'naming_pattern': 'Research - {filename}',
                'priority': 8
            },
            'processing_rules': {
                'auto_start': False,
                'retry_failed': True,
                'max_retries': 3
            },
            'is_public': True
        }
    ]
    
    for template_data in templates:
        # Check if template already exists
        existing = BatchTemplate.query.filter_by(name=template_data['name']).first()
        if not existing:
            template = BatchTemplate(**template_data)
            db.session.add(template)
            print(f"Created template: {template_data['name']}")
    
    db.session.commit()

if __name__ == '__main__':
    if migrate_batch_enhancements():
        print("\n✅ Batch enhancements migration completed successfully!")
        print("You can now use the enhanced batch functionality.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1)