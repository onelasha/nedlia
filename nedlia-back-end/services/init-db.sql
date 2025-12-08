-- =============================================================================
-- Nedlia Database Initialization
-- =============================================================================
-- This script runs on first PostgreSQL container startup
-- =============================================================================

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schemas for bounded contexts
CREATE SCHEMA IF NOT EXISTS placement;
CREATE SCHEMA IF NOT EXISTS campaign;
CREATE SCHEMA IF NOT EXISTS validation;
CREATE SCHEMA IF NOT EXISTS integration;

-- Grant permissions
GRANT ALL ON SCHEMA placement TO nedlia;
GRANT ALL ON SCHEMA campaign TO nedlia;
GRANT ALL ON SCHEMA validation TO nedlia;
GRANT ALL ON SCHEMA integration TO nedlia;

-- =============================================================================
-- Placement Context Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS placement.placements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL,
    product_id UUID NOT NULL,
    start_time DECIMAL(10, 3) NOT NULL,
    end_time DECIMAL(10, 3) NOT NULL,
    description TEXT,
    position JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    file_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID,
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT chk_time_range CHECK (end_time > start_time AND start_time >= 0),
    CONSTRAINT chk_status CHECK (status IN ('draft', 'active', 'archived'))
);

CREATE INDEX IF NOT EXISTS idx_placements_video ON placement.placements(video_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_placements_product ON placement.placements(product_id) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS placement.videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    duration DECIMAL(10, 3) NOT NULL,
    source_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'processing',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_duration CHECK (duration > 0),
    CONSTRAINT chk_status CHECK (status IN ('processing', 'ready', 'archived'))
);

-- =============================================================================
-- Campaign Context Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS campaign.advertisers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    contact_email VARCHAR(255) NOT NULL,
    billing_info JSONB,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT chk_status CHECK (status IN ('active', 'suspended'))
);

CREATE TABLE IF NOT EXISTS campaign.campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES campaign.advertisers(id),
    name VARCHAR(255) NOT NULL,
    budget DECIMAL(12, 2) NOT NULL,
    spent DECIMAL(12, 2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,

    CONSTRAINT chk_budget CHECK (spent <= budget),
    CONSTRAINT chk_dates CHECK (end_date > start_date),
    CONSTRAINT chk_status CHECK (status IN ('draft', 'active', 'paused', 'completed'))
);

CREATE TABLE IF NOT EXISTS campaign.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    advertiser_id UUID NOT NULL REFERENCES campaign.advertisers(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    assets JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

-- =============================================================================
-- Validation Context Tables
-- =============================================================================

CREATE TABLE IF NOT EXISTS validation.validation_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    issues JSONB DEFAULT '[]',
    summary JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    requested_by UUID,

    CONSTRAINT chk_status CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

-- =============================================================================
-- Event Log (for audit trail)
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.event_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(100) NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    aggregate_id UUID NOT NULL,
    data JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by UUID
);

CREATE INDEX IF NOT EXISTS idx_event_log_aggregate ON public.event_log(aggregate_type, aggregate_id);
CREATE INDEX IF NOT EXISTS idx_event_log_type ON public.event_log(event_type);

-- =============================================================================
-- Seed Data (for development)
-- =============================================================================

-- Insert test advertiser
INSERT INTO campaign.advertisers (id, name, contact_email, status)
VALUES ('00000000-0000-0000-0000-000000000001', 'Test Advertiser', 'test@example.com', 'active')
ON CONFLICT DO NOTHING;

-- Insert test campaign
INSERT INTO campaign.campaigns (id, advertiser_id, name, budget, status, start_date, end_date)
VALUES (
    '00000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000001',
    'Test Campaign',
    10000.00,
    'active',
    CURRENT_DATE,
    CURRENT_DATE + INTERVAL '30 days'
)
ON CONFLICT DO NOTHING;

-- Insert test product
INSERT INTO campaign.products (id, advertiser_id, name, category)
VALUES (
    '00000000-0000-0000-0000-000000000003',
    '00000000-0000-0000-0000-000000000001',
    'Test Product',
    'Electronics'
)
ON CONFLICT DO NOTHING;

-- Insert test video
INSERT INTO placement.videos (id, title, duration, status)
VALUES (
    '00000000-0000-0000-0000-000000000004',
    'Test Video',
    120.0,
    'ready'
)
ON CONFLICT DO NOTHING;

RAISE NOTICE 'Database initialization complete!';
