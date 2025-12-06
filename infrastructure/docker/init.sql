-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create main schema
CREATE SCHEMA IF NOT EXISTS jobseeker;

-- Set search path
SET search_path TO jobseeker, public;

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_premium BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User profiles table
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    skills JSONB DEFAULT '[]'::jsonb,
    experience_years INTEGER DEFAULT 0,
    preferences JSONB DEFAULT '{}'::jsonb,
    portfolio JSONB DEFAULT '{}'::jsonb,
    min_rate_usd DECIMAL(10, 2),
    max_hours_per_week INTEGER,
    availability JSONB DEFAULT '{}'::jsonb,
    profile_embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Jobs table
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    title TEXT NOT NULL,
    company VARCHAR(255),
    description TEXT,
    requirements JSONB DEFAULT '[]'::jsonb,
    skills JSONB DEFAULT '[]'::jsonb,
    rate_min DECIMAL(10, 2),
    rate_max DECIMAL(10, 2),
    rate_type VARCHAR(20), -- 'hourly', 'fixed', 'annual'
    location VARCHAR(255),
    remote BOOLEAN DEFAULT false,
    hours_per_week INTEGER,
    duration VARCHAR(100),
    posted_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    url TEXT,
    raw_data JSONB,
    job_embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_id)
);

-- Job matches table
CREATE TABLE IF NOT EXISTS job_matches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    score DECIMAL(5, 2) NOT NULL,
    score_breakdown JSONB DEFAULT '{}'::jsonb,
    explanation TEXT,
    status VARCHAR(50) DEFAULT 'new', -- 'new', 'viewed', 'saved', 'applied', 'rejected', 'interviewed', 'hired'
    proposal TEXT,
    applied_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, job_id)
);

-- User feedback table
CREATE TABLE IF NOT EXISTS user_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id) ON DELETE CASCADE,
    match_id UUID REFERENCES job_matches(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL, -- 'viewed', 'saved', 'applied', 'rejected', 'interviewed', 'hired'
    feedback_type VARCHAR(50), -- 'positive', 'negative', 'neutral'
    feedback_text TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Email ingestion tracking
CREATE TABLE IF NOT EXISTS email_ingestion (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_uid VARCHAR(255) NOT NULL,
    email_from VARCHAR(255),
    subject TEXT,
    received_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processed', 'failed', 'skipped'
    error_message TEXT,
    jobs_extracted INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(email_uid, email_from)
);

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'email', 'slack', 'webhook'
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    subject TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    sent_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ML model tracking
CREATE TABLE IF NOT EXISTS ml_models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(50) NOT NULL, -- 'scoring', 'embedding', 'proposal'
    version VARCHAR(50) NOT NULL,
    parameters JSONB DEFAULT '{}'::jsonb,
    metrics JSONB DEFAULT '{}'::jsonb,
    file_path TEXT,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(model_name, version)
);

-- Create indexes for better performance
CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_posted_at ON jobs(posted_at DESC);
CREATE INDEX idx_jobs_remote ON jobs(remote);
CREATE INDEX idx_jobs_skills ON jobs USING gin(skills);
CREATE INDEX idx_jobs_embedding ON jobs USING ivfflat (job_embedding vector_cosine_ops);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_skills ON user_profiles USING gin(skills);
CREATE INDEX idx_user_profiles_embedding ON user_profiles USING ivfflat (profile_embedding vector_cosine_ops);

CREATE INDEX idx_job_matches_user_id ON job_matches(user_id);
CREATE INDEX idx_job_matches_job_id ON job_matches(job_id);
CREATE INDEX idx_job_matches_score ON job_matches(score DESC);
CREATE INDEX idx_job_matches_status ON job_matches(status);

CREATE INDEX idx_user_feedback_user_id ON user_feedback(user_id);
CREATE INDEX idx_user_feedback_job_id ON user_feedback(job_id);
CREATE INDEX idx_user_feedback_action ON user_feedback(action);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to tables
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_jobs_updated_at BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_job_matches_updated_at BEFORE UPDATE ON job_matches
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();