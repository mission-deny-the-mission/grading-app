# Database Migration for Enhanced Batch System

This document explains how to safely upgrade your existing grading application database to support the new comprehensive batch system functionality.

## Migration Overview

The migration script [`migrate_batch_system.py`](migrate_batch_system.py) will:

- ✅ Create the new `batch_templates` table
- ✅ Add new columns to the existing `job_batches` table
- ✅ Update existing batch status values
- ✅ Create default batch templates
- ✅ Add foreign key relationships (PostgreSQL only)
- ✅ Verify the migration was successful

## Prerequisites

1. **Backup your database** before running the migration
2. Ensure all application servers are stopped
3. Have Python and required dependencies installed

## Running the Migration

### Step 1: Backup Your Database

**For SQLite:**
```bash
cp grading_app.db grading_app_backup_$(date +%Y%m%d_%H%M%S).db
```

**For PostgreSQL:**
```bash
pg_dump your_database_name > grading_app_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Run the Migration

```bash
python migrate_batch_system.py
```

The script will:
- Display progress information
- Show what changes are being made
- Verify the migration was successful
- Create a `migration_backup_info.json` file with migration details

### Step 3: Restart Your Application

After successful migration:
```bash
# If using systemd
sudo systemctl restart your-app-service

# If using PM2
pm2 restart your-app

# If running directly
python app.py
```

## Expected Output

A successful migration will show:
```
🚀 Starting Enhanced Batch System Migration
============================================================
📊 Database Type: sqlite
📊 Database URL: sqlite:///grading_app.db

🏗️ Creating batch_templates table...
  ✓ Created batch_templates table

📋 Migrating job_batches table...
  ✓ Added column: job_batches.updated_at
  ✓ Added column: job_batches.priority
  ✓ Added column: job_batches.tags
  [... more columns ...]

🔄 Updating batch status values...
  ✓ Set updated_at timestamps for existing batches

📝 Creating default batch templates...
  ✓ Created template: Academic Essay Grading
  ✓ Created template: Business Report Review
  ✓ Created template: Research Paper Analysis
  ✓ Created template: Creative Writing Assessment

✅ Verifying migration...
  ✓ All required tables exist
  ✓ All required columns exist
  ✓ Found 4 batch templates
  ✓ Found X existing batches

============================================================
🎉 Enhanced Batch System Migration Completed Successfully!
============================================================
```

## Migration Details

### New Database Schema

**BatchTemplate Table:**
- `id` - Unique identifier
- `name` - Template name
- `description` - Template description
- `category` - Template category
- `default_settings` - JSON settings
- `job_structure` - JSON job configuration
- `processing_rules` - JSON processing rules
- `is_public` - Public visibility flag
- `created_at` - Creation timestamp
- `created_by` - Creator identifier

**Enhanced JobBatch Table:**
- `updated_at` - Last update timestamp
- `priority` - Batch priority (1-10)
- `tags` - JSON array of tags
- `models_to_compare` - JSON model comparison settings
- `batch_settings` - JSON batch configuration
- `auto_assign_jobs` - Auto-assignment flag
- `total_jobs` - Total job count
- `completed_jobs` - Completed job count
- `failed_jobs` - Failed job count
- `deadline` - Batch deadline
- `started_at` - Start timestamp
- `completed_at` - Completion timestamp
- `estimated_completion` - Estimated completion time
- `template_id` - Associated template ID
- `created_by` - Creator identifier
- `shared_with` - JSON sharing configuration
- `saved_prompt_id` - Associated prompt ID
- `saved_marking_scheme_id` - Associated marking scheme ID

## Troubleshooting

### Migration Fails
1. Check the error message displayed
2. Ensure database is accessible
3. Verify you have write permissions
4. Restore from backup if needed

### Partial Migration
The script is designed to be idempotent - you can run it multiple times safely. It will skip already-migrated components.

### Rollback Required
If you need to rollback:
1. Stop the application
2. Restore from your backup
3. Restart with the old codebase

## Post-Migration Features

After successful migration, you'll have access to:

- **Batch Templates**: Reusable configurations for common grading scenarios
- **Enhanced Batch Management**: Priority scheduling, tags, deadlines
- **Improved Analytics**: Progress tracking, completion estimates
- **Bulk Operations**: Retry failed jobs, export results
- **Advanced Filtering**: Search by tags, status, dates
- **Template System**: Quick batch creation from templates

## Support

If you encounter issues:
1. Check the `migration_backup_info.json` file for migration details
2. Review application logs
3. Verify database connectivity
4. Ensure all dependencies are installed

The migration preserves all existing data while adding new functionality.