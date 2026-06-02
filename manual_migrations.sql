-- =========================================================================
-- SQL Commands for Excel Import Feature
-- =========================================================================

-- 1. Add new columns for Seekers to the 'users' table
ALTER TABLE users ADD COLUMN IF NOT EXISTS father_or_mother_name VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS gender VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS highest_qualification VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stream_specialization VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS college_institute_name VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_job_sector VARCHAR(200);

-- 2. Add new columns for Providers to the 'users' table
ALTER TABLE users ADD COLUMN IF NOT EXISTS job_roles_offering TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS specific_requirements TEXT;

-- 3. Create the table for storing randomly generated plain passwords during import
CREATE TABLE IF NOT EXISTS imported_user_passwords (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255),
    plain_password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc')
);

-- 4. Add index for faster email lookups on the passwords table
CREATE INDEX IF NOT EXISTS ix_imported_user_passwords_email ON imported_user_passwords (email);


-- =========================================================================
-- SQL Commands for Superadmin Role
-- =========================================================================

-- 5. Add 'superadmin' to the existing userrole enum
-- Note: 'ALTER TYPE ... ADD VALUE' cannot run inside a transaction block, 
-- so execute this statement on its own.
ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'superadmin';
