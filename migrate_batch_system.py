#!/usr/bin/env python3
"""
Comprehensive Database Migration for Enhanced Batch System
This script safely upgrades the existing database to support all new batch functionality.
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask
from sqlalchemy import text, inspect, MetaData, Table, Column, String, Integer, DateTime, Text, Boolean, JSON, Float
from sqlalchemy.exc import SQLAlchemyError
from models import db, BatchTemplate, JobBatch, GradingJob, SavedPrompt, SavedMarkingScheme

def create_app():
    """Create Flask app for migration."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///grading_app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def get_database_type(engine):
    """Determine database type."""
    return engine.dialect.name

def column_exists(engine, table_name, column_name):
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def table_exists(engine, table_name):
    """Check if a table exists."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def add_column_safe(engine, table_name, column_name, column_definition):
    """Safely add a column to a table."""
    if not column_exists(engine, table_name, column_name):
        try:
            db_type = get_database_type(engine)
            if db_type == 'sqlite':
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            else:  # PostgreSQL
                sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
            
            db.session.execute(text(sql))
            print(f"  ✓ Added column: {table_name}.{column_name}")
            return True
        except Exception as e:
            print(f"  ⚠ Warning: Could not add column {table_name}.{column_name}: {e}")
            return False
    else:
        print(f"  - Column already exists: {table_name}.{column_name}")
        return True

def create_batch_templates_table(engine):
    """Create the batch_templates table."""
    if not table_exists(engine, 'batch_templates'):
        try:
            db.create_all()  # This will create any missing tables
            print("  ✓ Created batch_templates table")
            return True
        except Exception as e:
            print(f"  ❌ Error creating batch_templates table: {e}")
            return False
    else:
        print("  - batch_templates table already exists")
        return True

def migrate_job_batches_table(engine):
    """Migrate the job_batches table with new columns."""
    print("\n📋 Migrating job_batches table...")
    
    # Define new columns to add
    new_columns = [
        ('updated_at', 'DATETIME'),
        ('priority', 'INTEGER DEFAULT 5'),
        ('tags', 'JSON' if get_database_type(engine) == 'postgresql' else 'TEXT'),
        ('models_to_compare', 'JSON' if get_database_type(engine) == 'postgresql' else 'TEXT'),
        ('batch_settings', 'JSON' if get_database_type(engine) == 'postgresql' else 'TEXT'),
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
        ('shared_with', 'JSON' if get_database_type(engine) == 'postgresql' else 'TEXT'),
        ('saved_prompt_id', 'VARCHAR(36)'),
        ('saved_marking_scheme_id', 'VARCHAR(36)')
    ]
    
    success = True
    for column_name, column_def in new_columns:
        if not add_column_safe(engine, 'job_batches', column_name, column_def):
            success = False
    
    return success

def update_batch_status_values(engine):
    """Update existing batch status values."""
    print("\n🔄 Updating batch status values...")
    
    try:
        # Update any existing 'pending' status to 'draft' for new status scheme
        result = db.session.execute(text("SELECT COUNT(*) FROM job_batches WHERE status = 'pending'"))
        pending_count = result.scalar()
        
        if pending_count > 0:
            db.session.execute(text("UPDATE job_batches SET status = 'draft' WHERE status = 'pending'"))
            print(f"  ✓ Updated {pending_count} batches from 'pending' to 'draft' status")
        else:
            print("  - No status updates needed")
        
        # Set updated_at for existing records
        db.session.execute(text("UPDATE job_batches SET updated_at = created_at WHERE updated_at IS NULL"))
        print("  ✓ Set updated_at timestamps for existing batches")
        
        return True
    except Exception as e:
        print(f"  ❌ Error updating status values: {e}")
        return False

def create_foreign_key_constraints(engine):
    """Add foreign key constraints if using PostgreSQL."""
    if get_database_type(engine) != 'postgresql':
        print("  - Skipping foreign key constraints (SQLite doesn't enforce them)")
        return True
    
    print("\n🔗 Adding foreign key constraints...")
    
    constraints = [
        {
            'table': 'job_batches',
            'constraint': 'fk_batch_template',
            'column': 'template_id',
            'references': 'batch_templates(id)'
        },
        {
            'table': 'job_batches',
            'constraint': 'fk_batch_saved_prompt',
            'column': 'saved_prompt_id',
            'references': 'saved_prompts(id)'
        },
        {
            'table': 'job_batches',
            'constraint': 'fk_batch_saved_marking_scheme',
            'column': 'saved_marking_scheme_id',
            'references': 'saved_marking_schemes(id)'
        }
    ]
    
    success = True
    for constraint in constraints:
        try:
            sql = f"""
                ALTER TABLE {constraint['table']} 
                ADD CONSTRAINT {constraint['constraint']} 
                FOREIGN KEY ({constraint['column']}) REFERENCES {constraint['references']}
            """
            db.session.execute(text(sql))
            print(f"  ✓ Added constraint: {constraint['constraint']}")
        except Exception as e:
            print(f"  ⚠ Warning: Could not add constraint {constraint['constraint']}: {e}")
            success = False
    
    return success

def create_default_batch_templates():
    """Create default batch templates."""
    print("\n📝 Creating default batch templates...")
    
    templates_data = [
        {
            'name': 'Academic Essay Grading',
            'description': 'Standard template for grading academic essays and papers with comprehensive criteria',
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
            'is_public': True,
            'created_by': 'system'
        },
        {
            'name': 'Business Report Review',
            'description': 'Template for reviewing business reports and proposals with professional standards',
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
            'is_public': True,
            'created_by': 'system'
        },
        {
            'name': 'Research Paper Analysis',
            'description': 'Comprehensive template for analyzing research papers with academic rigor',
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
            'is_public': True,
            'created_by': 'system'
        },
        {
            'name': 'Creative Writing Assessment',
            'description': 'Template for evaluating creative writing with focus on narrative and style',
            'category': 'academic',
            'default_settings': {
                'provider': 'openrouter',
                'model': 'anthropic/claude-3-5-sonnet-20241022',
                'temperature': 0.4,
                'max_tokens': 2500
            },
            'job_structure': {
                'auto_naming': True,
                'naming_pattern': 'Creative - {filename}',
                'priority': 5
            },
            'processing_rules': {
                'auto_start': False,
                'retry_failed': True,
                'max_retries': 3
            },
            'is_public': True,
            'created_by': 'system'
        }
    ]
    
    created_count = 0
    for template_data in templates_data:
        # Check if template already exists
        existing = BatchTemplate.query.filter_by(name=template_data['name']).first()
        if not existing:
            try:
                template = BatchTemplate(**template_data)
                db.session.add(template)
                created_count += 1
                print(f"  ✓ Created template: {template_data['name']}")
            except Exception as e:
                print(f"  ❌ Error creating template {template_data['name']}: {e}")
        else:
            print(f"  - Template already exists: {template_data['name']}")
    
    if created_count > 0:
        try:
            db.session.commit()
            print(f"  ✓ Successfully created {created_count} new templates")
        except Exception as e:
            print(f"  ❌ Error committing templates: {e}")
            db.session.rollback()
            return False
    
    return True

def verify_migration():
    """Verify that the migration was successful."""
    print("\n✅ Verifying migration...")
    
    try:
        # Check tables exist
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        required_tables = ['job_batches', 'batch_templates', 'grading_jobs']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"  ❌ Missing tables: {missing_tables}")
            return False
        
        print("  ✓ All required tables exist")
        
        # Check key columns exist
        job_batches_columns = [col['name'] for col in inspector.get_columns('job_batches')]
        required_columns = ['priority', 'tags', 'deadline', 'template_id']
        missing_columns = [c for c in required_columns if c not in job_batches_columns]
        
        if missing_columns:
            print(f"  ❌ Missing columns in job_batches: {missing_columns}")
            return False
        
        print("  ✓ All required columns exist")
        
        # Check templates were created
        template_count = BatchTemplate.query.count()
        print(f"  ✓ Found {template_count} batch templates")
        
        # Check existing batches are accessible
        batch_count = JobBatch.query.count()
        print(f"  ✓ Found {batch_count} existing batches")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Verification failed: {e}")
        return False

def create_backup_info():
    """Create a backup information file."""
    backup_info = {
        'migration_date': datetime.now().isoformat(),
        'database_url': os.getenv('DATABASE_URL', 'sqlite:///grading_app.db'),
        'migration_version': '1.0.0',
        'description': 'Enhanced Batch System Migration',
        'changes': [
            'Added BatchTemplate table',
            'Enhanced JobBatch table with new columns',
            'Updated batch status values',
            'Created default batch templates',
            'Added foreign key relationships'
        ]
    }
    
    try:
        with open('migration_backup_info.json', 'w') as f:
            json.dump(backup_info, f, indent=2)
        print("  ✓ Created migration backup info file")
    except Exception as e:
        print(f"  ⚠ Warning: Could not create backup info: {e}")

def main():
    """Main migration function."""
    print("🚀 Starting Enhanced Batch System Migration")
    print("=" * 60)
    
    # Create app context
    app = create_app()
    
    with app.app_context():
        try:
            # Get database info
            db_type = get_database_type(db.engine)
            print(f"📊 Database Type: {db_type}")
            print(f"📊 Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
            
            # Create backup info
            create_backup_info()
            
            # Step 1: Create batch_templates table
            print("\n🏗️ Creating batch_templates table...")
            if not create_batch_templates_table(db.engine):
                print("❌ Failed to create batch_templates table")
                return False
            
            # Step 2: Migrate job_batches table
            if not migrate_job_batches_table(db.engine):
                print("❌ Failed to migrate job_batches table")
                return False
            
            # Step 3: Update existing data
            if not update_batch_status_values(db.engine):
                print("❌ Failed to update batch status values")
                return False
            
            # Step 4: Create foreign key constraints (PostgreSQL only)
            create_foreign_key_constraints(db.engine)
            
            # Step 5: Create default templates
            if not create_default_batch_templates():
                print("❌ Failed to create default batch templates")
                return False
            
            # Commit all changes
            try:
                db.session.commit()
                print("\n💾 All changes committed successfully")
            except Exception as e:
                print(f"\n❌ Error committing changes: {e}")
                db.session.rollback()
                return False
            
            # Step 6: Verify migration
            if not verify_migration():
                print("❌ Migration verification failed")
                return False
            
            print("\n" + "=" * 60)
            print("🎉 Enhanced Batch System Migration Completed Successfully!")
            print("=" * 60)
            print("\n📋 Migration Summary:")
            print("  ✓ Created BatchTemplate table with default templates")
            print("  ✓ Enhanced JobBatch table with advanced features")
            print("  ✓ Updated existing batch status values")
            print("  ✓ Added foreign key relationships")
            print("  ✓ Created migration backup info")
            
            print("\n🚀 Next Steps:")
            print("  1. Restart your application servers")
            print("  2. Test batch creation and management")
            print("  3. Explore new template functionality")
            print("  4. Review batch analytics and export features")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed with error: {e}")
            try:
                db.session.rollback()
                print("  ↩️ Database changes rolled back")
            except:
                pass
            return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)