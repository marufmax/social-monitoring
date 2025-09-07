-- =========================
-- PERFORMANCE INDEXES
-- Social Media Monitor Database
-- =========================

-- Required PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =========================
-- CORE ENTITY INDEXES
-- =========================

-- Workspaces
CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces (owner_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_plan ON workspaces (plan_type);

-- Monitors
CREATE INDEX IF NOT EXISTS idx_monitors_workspace_status ON monitors (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_monitors_keywords ON monitors USING GIN (keywords);
CREATE INDEX IF NOT EXISTS idx_monitors_platforms ON monitors USING GIN (platforms);
CREATE INDEX IF NOT EXISTS idx_monitors_created_by ON monitors (created_by);
CREATE INDEX IF NOT EXISTS idx_monitors_active ON monitors (workspace_id) WHERE status = 'active';

-- Social Users (for influencer detection and performance)
CREATE INDEX IF NOT EXISTS idx_social_users_platform_external ON social_users (platform_id, external_user_id);
CREATE INDEX IF NOT EXISTS idx_social_users_influence ON social_users (influence_score DESC) WHERE influence_score > 0;
CREATE INDEX IF NOT EXISTS idx_social_users_followers ON social_users (follower_count DESC);
CREATE INDEX IF NOT EXISTS idx_social_users_verified ON social_users (verified) WHERE verified = TRUE;
CREATE INDEX IF NOT EXISTS idx_social_users_username ON social_users (platform_id, LOWER(username));

-- =========================
-- MENTIONS & CONTENT INDEXES
-- =========================

-- Primary mentions table (before partitioning)
CREATE INDEX IF NOT EXISTS idx_mentions_published_at ON mentions (published_at);
CREATE INDEX IF NOT EXISTS idx_mentions_platform_published ON mentions (platform_id, published_at);
CREATE INDEX IF NOT EXISTS idx_mentions_social_user ON mentions (social_user_id);
CREATE INDEX IF NOT EXISTS idx_mentions_sentiment ON mentions (sentiment_score) WHERE sentiment_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mentions_category ON mentions (category) WHERE category IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mentions_priority ON mentions (priority_score) WHERE priority_score > 0;
CREATE INDEX IF NOT EXISTS idx_mentions_external_id ON mentions (platform_id, external_post_id);

-- Full-text search indexes
CREATE INDEX IF NOT EXISTS idx_mentions_content_fts ON mentions USING GIN (to_tsvector('english', content));
CREATE INDEX IF NOT EXISTS idx_mentions_content_trigram ON mentions USING GIN (content gin_trgm_ops);

-- Monitor mentions (relationship table)
CREATE INDEX IF NOT EXISTS idx_monitor_mentions_monitor_detected ON monitor_mentions (monitor_id, detected_at);
CREATE INDEX IF NOT EXISTS idx_monitor_mentions_mention ON monitor_mentions (mention_id);
CREATE INDEX IF NOT EXISTS idx_monitor_mentions_confidence ON monitor_mentions (confidence_score DESC) WHERE confidence_score > 0.5;

-- =========================
-- COLLABORATION INDEXES
-- =========================

-- Mention Assignments
CREATE INDEX IF NOT EXISTS idx_mention_assignments_workspace_status ON mention_assignments (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_mention_assignments_assigned_to ON mention_assignments (assigned_to) WHERE assigned_to IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mention_assignments_due_date ON mention_assignments (due_date) WHERE due_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mention_assignments_priority ON mention_assignments (priority DESC);
CREATE INDEX IF NOT EXISTS idx_mention_assignments_created_at ON mention_assignments (created_at);

-- Mention Responses
CREATE INDEX IF NOT EXISTS idx_mention_responses_mention ON mention_responses (mention_id);
CREATE INDEX IF NOT EXISTS idx_mention_responses_assignment ON mention_responses (assignment_id);
CREATE INDEX IF NOT EXISTS idx_mention_responses_status ON mention_responses (response_status);
CREATE INDEX IF NOT EXISTS idx_mention_responses_responded_by ON mention_responses (responded_by);

-- =========================
-- ALERT SYSTEM INDEXES
-- =========================

-- Alerts
CREATE INDEX IF NOT EXISTS idx_alerts_monitor_triggered ON alerts (monitor_id, triggered_at);
CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts (severity) WHERE severity IN ('high', 'critical');
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts (status);

-- Alert Deliveries
CREATE INDEX IF NOT EXISTS idx_alert_deliveries_status ON alert_deliveries (status) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_alert_deliveries_scheduled ON alert_deliveries (scheduled_for) WHERE scheduled_for IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_alert_deliveries_channel ON alert_deliveries (channel_type);

-- =========================
-- ANALYTICS INDEXES
-- =========================

-- Hourly Analytics
CREATE INDEX IF NOT EXISTS idx_analytics_hourly_monitor_bucket ON monitor_analytics_hourly (monitor_id, hour_bucket);
CREATE INDEX IF NOT EXISTS idx_analytics_hourly_workspace ON monitor_analytics_hourly (workspace_id, hour_bucket);

-- Daily Analytics
CREATE INDEX IF NOT EXISTS idx_analytics_daily_monitor_date ON monitor_analytics_daily (monitor_id, date_bucket);
CREATE INDEX IF NOT EXISTS idx_analytics_daily_workspace ON monitor_analytics_daily (workspace_id, date_bucket);

-- =========================
-- USAGE & BILLING INDEXES
-- =========================

-- Usage Tracking
CREATE INDEX IF NOT EXISTS idx_usage_tracking_workspace_period ON usage_tracking (workspace_id, period_start);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_period ON usage_tracking (period_start, period_end);

-- =========================
-- DEDUPLICATION INDEXES
-- =========================

-- Mention Fingerprints
CREATE INDEX IF NOT EXISTS idx_fingerprints_content_hash ON mention_fingerprints (content_hash);
CREATE INDEX IF NOT EXISTS idx_fingerprints_similarity ON mention_fingerprints (similarity_hash);
CREATE INDEX IF NOT EXISTS idx_fingerprints_url_hash ON mention_fingerprints (url_hash) WHERE url_hash IS NOT NULL;

-- =========================
-- NOTIFICATION INDEXES
-- =========================

-- Notification Queue
CREATE INDEX IF NOT EXISTS idx_notification_queue_processing ON notification_queue (status, scheduled_for, priority)
WHERE status IN ('pending', 'processing');
CREATE INDEX IF NOT EXISTS idx_notification_queue_recipient ON notification_queue (recipient_id, created_at);

-- Notification Preferences
CREATE INDEX IF NOT EXISTS idx_notification_pref_user_workspace ON notification_preferences (user_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_notification_pref_enabled ON notification_preferences (notification_type) WHERE enabled = TRUE;

-- =========================
-- SYSTEM & AUDIT INDEXES
-- =========================

-- Audit Logs
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_action ON audit_logs (user_id, action);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_logs (resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_workspace ON audit_logs (workspace_id, created_at);

-- System Health
CREATE INDEX IF NOT EXISTS idx_system_health_component_time ON system_health (component, last_check_at);
CREATE INDEX IF NOT EXISTS idx_system_health_status ON system_health (status) WHERE status != 'healthy';

-- Data Exports
CREATE INDEX IF NOT EXISTS idx_data_exports_workspace ON data_exports (workspace_id, created_at);
CREATE INDEX IF NOT EXISTS idx_data_exports_status ON data_exports (status) WHERE status IN ('pending', 'processing');

-- =========================
-- INTEGRATION INDEXES
-- =========================

-- Workspace Integrations
CREATE INDEX IF NOT EXISTS idx_workspace_integrations_workspace ON workspace_integrations (workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_workspace_integrations_provider ON workspace_integrations (provider_id);

-- =========================
-- COMPOSITE INDEXES FOR COMMON QUERIES
-- =========================

-- Mention dashboard queries
CREATE INDEX IF NOT EXISTS idx_mentions_dashboard ON mentions (workspace_id, published_at DESC, status)
WHERE status != 'deleted';

-- Real-time monitoring
CREATE INDEX IF NOT EXISTS idx_mentions_realtime ON mentions (published_at DESC, platform_id)
WHERE published_at > (NOW() - INTERVAL '24 hours');

-- Sentiment analysis queries
CREATE INDEX IF NOT EXISTS idx_mentions_sentiment_analysis ON mentions (workspace_id, sentiment_score, published_at)
WHERE sentiment_score IS NOT NULL;

-- Influencer tracking
CREATE INDEX IF NOT EXISTS idx_mentions_influencer ON mentions (social_user_id, published_at)
WHERE social_user_id IN (
    SELECT id FROM social_users WHERE influence_score > 50
);

-- =========================
-- PARTIAL INDEXES FOR EFFICIENCY
-- =========================

-- Only index active monitors
CREATE INDEX IF NOT EXISTS idx_monitors_active_only ON monitors (workspace_id, created_at)
WHERE status = 'active';

-- Only index unprocessed mentions
CREATE INDEX IF NOT EXISTS idx_mentions_unprocessed ON mentions (created_at)
WHERE processed_at IS NULL;

-- Only index pending alerts
CREATE INDEX IF NOT EXISTS idx_alerts_pending ON alerts (monitor_id, created_at)
WHERE status = 'pending';

-- =========================
-- VECTOR/SIMILARITY INDEXES
-- =========================

-- Content embeddings for semantic search (if using pgvector)
CREATE INDEX IF NOT EXISTS idx_mentions_embedding ON mentions USING ivfflat (content_embedding vector_cosine_ops)
WITH (lists = 100) WHERE content_embedding IS NOT NULL;

-- =========================
-- CLEANUP & MAINTENANCE
-- =========================

-- -- Analyze tables after creating indexes
-- ANALYZE monitors;
-- ANALYZE mentions;
-- ANALYZE social_users;
-- ANALYZE monitor_mentions;
-- ANALYZE mention_assignments;
-- ANALYZE alerts;
-- ANALYZE monitor_analytics_hourly;
-- ANALYZE usage_tracking;