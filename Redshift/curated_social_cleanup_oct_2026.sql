-- =====================================================================
-- Drop list for pgat.curated_social  (115 objects: tables + views)
-- Run in ONE session, top to bottom. Nothing uses CASCADE.
-- Step 1: pre-check (read-only)   Step 2: drop what can be dropped
-- Step 3: results                 Step 4: blockers to send to end user
-- =====================================================================

-- ---------- STEP 1a: names in the list that do not exist (already gone / typo)
SELECT l.obj_name AS not_found_in_curated_social
FROM (
  SELECT 'daily_primary' AS obj_name
  UNION ALL SELECT 'daily_primary_paid' AS obj_name
  UNION ALL SELECT 'daily_social_player' AS obj_name
  UNION ALL SELECT 'dashboard_weekly' AS obj_name
  UNION ALL SELECT 'dashboard_weekly_player_social' AS obj_name
  UNION ALL SELECT 'dashboard_weekly_social_post_player' AS obj_name
  UNION ALL SELECT 'dashboard_weekly_social_post_player_v2' AS obj_name
  UNION ALL SELECT 'int_daily_primary' AS obj_name
  UNION ALL SELECT 'int_metadata_v2' AS obj_name
  UNION ALL SELECT 'int_mt_sprout_weekly_media_player' AS obj_name
  UNION ALL SELECT 'int_weekly_cross_channel_stage' AS obj_name
  UNION ALL SELECT 'int_weekly_primary' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_agg_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_player_sprout' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_player_v2' AS obj_name
  UNION ALL SELECT 'monthly_kpi_mvp_index' AS obj_name
  UNION ALL SELECT 'post_metadata_v2' AS obj_name
  UNION ALL SELECT 'post_metrics' AS obj_name
  UNION ALL SELECT 'post_metrics_metadata_sprout' AS obj_name
  UNION ALL SELECT 'post_metrics_metadata_sprout_updated' AS obj_name
  UNION ALL SELECT 'post_metrics_metadata_v2' AS obj_name
  UNION ALL SELECT 'post_metrics_old' AS obj_name
  UNION ALL SELECT 'post_metrics_updated' AS obj_name
  UNION ALL SELECT 'post_metrics_v2' AS obj_name
  UNION ALL SELECT 'weekly_primary' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_level_facebook' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_level_instagram' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_level_twitter' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_metrics' AS obj_name
  UNION ALL SELECT 'int_daily_engagement_rate_backfill' AS obj_name
  UNION ALL SELECT 'int_daily_kpi_social_player' AS obj_name
  UNION ALL SELECT 'int_daily_metrics' AS obj_name
  UNION ALL SELECT 'int_daily_primary_ig_collabs' AS obj_name
  UNION ALL SELECT 'int_daily_primary_paid' AS obj_name
  UNION ALL SELECT 'int_daily_primary_update' AS obj_name
  UNION ALL SELECT 'int_daily_primary_v2' AS obj_name
  UNION ALL SELECT 'int_daily_social_player' AS obj_name
  UNION ALL SELECT 'int_daily_social_player_agg' AS obj_name
  UNION ALL SELECT 'int_daily_social_player_stage' AS obj_name
  UNION ALL SELECT 'int_date_level_tiktok' AS obj_name
  UNION ALL SELECT 'int_date_level_tiktok_v2' AS obj_name
  UNION ALL SELECT 'int_date_level_youtube' AS obj_name
  UNION ALL SELECT 'int_date_level_youtube_v2' AS obj_name
  UNION ALL SELECT 'int_facebook_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_facebook_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_facebook_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_instagram_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_instagram_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_instagram_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata' AS obj_name
  UNION ALL SELECT 'int_metadata_contentpillar_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_facebook_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_formatted' AS obj_name
  UNION ALL SELECT 'int_metadata_franchises_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_instagram_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_facebook_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_historical' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_instagram_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_tiktok_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_x_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_youtube_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_tiktok_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_trackingtags_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_x_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_youtube_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_facebook' AS obj_name
  UNION ALL SELECT 'int_post_level_facebook_updated' AS obj_name
  UNION ALL SELECT 'int_post_level_facebook_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram_collab' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram_collab_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_tiktok' AS obj_name
  UNION ALL SELECT 'int_post_level_tiktok_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_twitter' AS obj_name
  UNION ALL SELECT 'int_post_level_x_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_youtube_v2' AS obj_name
  UNION ALL SELECT 'int_post_metrics' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata_sprout' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata_sprout_new' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_post_metrics_test' AS obj_name
  UNION ALL SELECT 'int_post_metrics_test_v2' AS obj_name
  UNION ALL SELECT 'int_post_metrics_updated' AS obj_name
  UNION ALL SELECT 'int_social_metadata' AS obj_name
  UNION ALL SELECT 'int_sprout_tags' AS obj_name
  UNION ALL SELECT 'int_tiktok_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_tiktok_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_tiktok_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_weekly_cross_channel' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_social_player' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_social_player_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_social_trn_factors' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_stage' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_trn_factors' AS obj_name
  UNION ALL SELECT 'int_weekly_primary_historical' AS obj_name
  UNION ALL SELECT 'int_weekly_primary_yt' AS obj_name
  UNION ALL SELECT 'int_weekly_social_franchise' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_agg' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_stage' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_stage_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_player' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_type' AS obj_name
  UNION ALL SELECT 'int_x_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_x_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_x_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_youtube_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_youtube_metadata_pgatour_sprout_updated' AS obj_name
) l
LEFT JOIN (SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'curated_social') e ON e.relname = l.obj_name
WHERE e.relname IS NULL;

-- ---------- STEP 1b: EXTERNAL LATE-BINDING views that reference a list object
-- (exact-name match; excludes views that are themselves in the drop list).
-- These do NOT block a drop but WILL break afterward -> get approval or remove the name
-- from the list. Normal (early-binding) dependents are handled by Step 4.
-- Matches the schema-qualified reference curated_social.<name> (late-binding views must
-- qualify), so same-named objects in other schemas (e.g. dbt_<user>_* dev schemas) are ignored.
SELECT v.schemaname AS view_schema, v.viewname AS view_name, l.obj_name AS references_list_object
FROM pg_views v
JOIN (
  SELECT 'daily_primary' AS obj_name
  UNION ALL SELECT 'daily_primary_paid' AS obj_name
  UNION ALL SELECT 'daily_social_player' AS obj_name
  UNION ALL SELECT 'dashboard_weekly' AS obj_name
  UNION ALL SELECT 'dashboard_weekly_player_social' AS obj_name
  UNION ALL SELECT 'dashboard_weekly_social_post_player' AS obj_name
  UNION ALL SELECT 'dashboard_weekly_social_post_player_v2' AS obj_name
  UNION ALL SELECT 'int_daily_primary' AS obj_name
  UNION ALL SELECT 'int_metadata_v2' AS obj_name
  UNION ALL SELECT 'int_mt_sprout_weekly_media_player' AS obj_name
  UNION ALL SELECT 'int_weekly_cross_channel_stage' AS obj_name
  UNION ALL SELECT 'int_weekly_primary' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_agg_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_player_sprout' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_player_v2' AS obj_name
  UNION ALL SELECT 'monthly_kpi_mvp_index' AS obj_name
  UNION ALL SELECT 'post_metadata_v2' AS obj_name
  UNION ALL SELECT 'post_metrics' AS obj_name
  UNION ALL SELECT 'post_metrics_metadata_sprout' AS obj_name
  UNION ALL SELECT 'post_metrics_metadata_sprout_updated' AS obj_name
  UNION ALL SELECT 'post_metrics_metadata_v2' AS obj_name
  UNION ALL SELECT 'post_metrics_old' AS obj_name
  UNION ALL SELECT 'post_metrics_updated' AS obj_name
  UNION ALL SELECT 'post_metrics_v2' AS obj_name
  UNION ALL SELECT 'weekly_primary' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_level_facebook' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_level_instagram' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_level_twitter' AS obj_name
  UNION ALL SELECT 'int_ad_account_post_metrics' AS obj_name
  UNION ALL SELECT 'int_daily_engagement_rate_backfill' AS obj_name
  UNION ALL SELECT 'int_daily_kpi_social_player' AS obj_name
  UNION ALL SELECT 'int_daily_metrics' AS obj_name
  UNION ALL SELECT 'int_daily_primary_ig_collabs' AS obj_name
  UNION ALL SELECT 'int_daily_primary_paid' AS obj_name
  UNION ALL SELECT 'int_daily_primary_update' AS obj_name
  UNION ALL SELECT 'int_daily_primary_v2' AS obj_name
  UNION ALL SELECT 'int_daily_social_player' AS obj_name
  UNION ALL SELECT 'int_daily_social_player_agg' AS obj_name
  UNION ALL SELECT 'int_daily_social_player_stage' AS obj_name
  UNION ALL SELECT 'int_date_level_tiktok' AS obj_name
  UNION ALL SELECT 'int_date_level_tiktok_v2' AS obj_name
  UNION ALL SELECT 'int_date_level_youtube' AS obj_name
  UNION ALL SELECT 'int_date_level_youtube_v2' AS obj_name
  UNION ALL SELECT 'int_facebook_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_facebook_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_facebook_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_instagram_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_instagram_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_instagram_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata' AS obj_name
  UNION ALL SELECT 'int_metadata_contentpillar_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_facebook_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_formatted' AS obj_name
  UNION ALL SELECT 'int_metadata_franchises_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_instagram_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_facebook_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_historical' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_instagram_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_tiktok_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_x_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_pgatour_youtube_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_metadata_tiktok_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_trackingtags_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_x_v2' AS obj_name
  UNION ALL SELECT 'int_metadata_youtube_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_facebook' AS obj_name
  UNION ALL SELECT 'int_post_level_facebook_updated' AS obj_name
  UNION ALL SELECT 'int_post_level_facebook_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram_collab' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram_collab_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_instagram_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_tiktok' AS obj_name
  UNION ALL SELECT 'int_post_level_tiktok_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_twitter' AS obj_name
  UNION ALL SELECT 'int_post_level_x_v2' AS obj_name
  UNION ALL SELECT 'int_post_level_youtube_v2' AS obj_name
  UNION ALL SELECT 'int_post_metrics' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata_sprout' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata_sprout_new' AS obj_name
  UNION ALL SELECT 'int_post_metrics_metadata_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_post_metrics_test' AS obj_name
  UNION ALL SELECT 'int_post_metrics_test_v2' AS obj_name
  UNION ALL SELECT 'int_post_metrics_updated' AS obj_name
  UNION ALL SELECT 'int_social_metadata' AS obj_name
  UNION ALL SELECT 'int_sprout_tags' AS obj_name
  UNION ALL SELECT 'int_tiktok_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_tiktok_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_tiktok_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_weekly_cross_channel' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_social_player' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_social_player_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_social_trn_factors' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_stage' AS obj_name
  UNION ALL SELECT 'int_weekly_kpi_trn_factors' AS obj_name
  UNION ALL SELECT 'int_weekly_primary_historical' AS obj_name
  UNION ALL SELECT 'int_weekly_primary_yt' AS obj_name
  UNION ALL SELECT 'int_weekly_social_franchise' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_agg' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_stage' AS obj_name
  UNION ALL SELECT 'int_weekly_social_player_stage_v2' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_player' AS obj_name
  UNION ALL SELECT 'int_weekly_social_post_type' AS obj_name
  UNION ALL SELECT 'int_x_metadata_pgatour' AS obj_name
  UNION ALL SELECT 'int_x_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_x_metadata_pgatour_sprout_updated' AS obj_name
  UNION ALL SELECT 'int_youtube_metadata_pgatour_sprout' AS obj_name
  UNION ALL SELECT 'int_youtube_metadata_pgatour_sprout_updated' AS obj_name
) l ON LOWER(v.definition) ~ ('curated_social"?\\."?' || l.obj_name || '([^a-z0-9_]|$)')
WHERE v.schemaname NOT IN ('pg_catalog','information_schema')
  AND v.schemaname NOT LIKE 'dbt%'   -- ignore dbt_* developer sandbox schemas
  AND LOWER(v.definition) LIKE '%no schema binding%'
  AND NOT (v.schemaname = 'curated_social' AND v.viewname IN (
  'daily_primary',
  'daily_primary_paid',
  'daily_social_player',
  'dashboard_weekly',
  'dashboard_weekly_player_social',
  'dashboard_weekly_social_post_player',
  'dashboard_weekly_social_post_player_v2',
  'int_daily_primary',
  'int_metadata_v2',
  'int_mt_sprout_weekly_media_player',
  'int_weekly_cross_channel_stage',
  'int_weekly_primary',
  'int_weekly_social_player_agg_v2',
  'int_weekly_social_player_v2',
  'int_weekly_social_post_player_sprout',
  'int_weekly_social_post_player_v2',
  'monthly_kpi_mvp_index',
  'post_metadata_v2',
  'post_metrics',
  'post_metrics_metadata_sprout',
  'post_metrics_metadata_sprout_updated',
  'post_metrics_metadata_v2',
  'post_metrics_old',
  'post_metrics_updated',
  'post_metrics_v2',
  'weekly_primary',
  'int_ad_account_post_level_facebook',
  'int_ad_account_post_level_instagram',
  'int_ad_account_post_level_twitter',
  'int_ad_account_post_metrics',
  'int_daily_engagement_rate_backfill',
  'int_daily_kpi_social_player',
  'int_daily_metrics',
  'int_daily_primary_ig_collabs',
  'int_daily_primary_paid',
  'int_daily_primary_update',
  'int_daily_primary_v2',
  'int_daily_social_player',
  'int_daily_social_player_agg',
  'int_daily_social_player_stage',
  'int_date_level_tiktok',
  'int_date_level_tiktok_v2',
  'int_date_level_youtube',
  'int_date_level_youtube_v2',
  'int_facebook_metadata_pgatour',
  'int_facebook_metadata_pgatour_sprout',
  'int_facebook_metadata_pgatour_sprout_updated',
  'int_instagram_metadata_pgatour',
  'int_instagram_metadata_pgatour_sprout',
  'int_instagram_metadata_pgatour_sprout_updated',
  'int_metadata',
  'int_metadata_contentpillar_v2',
  'int_metadata_facebook_v2',
  'int_metadata_formatted',
  'int_metadata_franchises_v2',
  'int_metadata_instagram_v2',
  'int_metadata_pgatour',
  'int_metadata_pgatour_facebook_sprout_updated',
  'int_metadata_pgatour_historical',
  'int_metadata_pgatour_instagram_sprout_updated',
  'int_metadata_pgatour_sprout',
  'int_metadata_pgatour_sprout_updated',
  'int_metadata_pgatour_tiktok_sprout_updated',
  'int_metadata_pgatour_x_sprout_updated',
  'int_metadata_pgatour_youtube_sprout_updated',
  'int_metadata_tiktok_v2',
  'int_metadata_trackingtags_v2',
  'int_metadata_x_v2',
  'int_metadata_youtube_v2',
  'int_post_level_facebook',
  'int_post_level_facebook_updated',
  'int_post_level_facebook_v2',
  'int_post_level_instagram',
  'int_post_level_instagram_collab',
  'int_post_level_instagram_collab_v2',
  'int_post_level_instagram_v2',
  'int_post_level_tiktok',
  'int_post_level_tiktok_v2',
  'int_post_level_twitter',
  'int_post_level_x_v2',
  'int_post_level_youtube_v2',
  'int_post_metrics',
  'int_post_metrics_metadata',
  'int_post_metrics_metadata_sprout',
  'int_post_metrics_metadata_sprout_new',
  'int_post_metrics_metadata_sprout_updated',
  'int_post_metrics_test',
  'int_post_metrics_test_v2',
  'int_post_metrics_updated',
  'int_social_metadata',
  'int_sprout_tags',
  'int_tiktok_metadata_pgatour',
  'int_tiktok_metadata_pgatour_sprout',
  'int_tiktok_metadata_pgatour_sprout_updated',
  'int_weekly_cross_channel',
  'int_weekly_kpi',
  'int_weekly_kpi_social_player',
  'int_weekly_kpi_social_player_v2',
  'int_weekly_kpi_social_trn_factors',
  'int_weekly_kpi_stage',
  'int_weekly_kpi_trn_factors',
  'int_weekly_primary_historical',
  'int_weekly_primary_yt',
  'int_weekly_social_franchise',
  'int_weekly_social_player',
  'int_weekly_social_player_agg',
  'int_weekly_social_player_stage',
  'int_weekly_social_player_stage_v2',
  'int_weekly_social_post_player',
  'int_weekly_social_post_type',
  'int_x_metadata_pgatour',
  'int_x_metadata_pgatour_sprout',
  'int_x_metadata_pgatour_sprout_updated',
  'int_youtube_metadata_pgatour_sprout',
  'int_youtube_metadata_pgatour_sprout_updated'
  ))
ORDER BY 1, 2, 3;

-- ---------- STEP 2: drop loop
-- Views depend on views/tables inside the list, so a single pass can fail on
-- ordering. The loop repeats until a full pass drops nothing; anything still
-- left is blocked by something (see Step 4).
CREATE TEMP TABLE drop_log (obj_name varchar(256), obj_type varchar(30), dropped_at timestamp);

CREATE OR REPLACE PROCEDURE public.sp_drop_curated_social_list()
AS $$
DECLARE
  r RECORD;
  progress int;
  ddl_type varchar(30);
BEGIN
  LOOP
    progress := 0;
    FOR r IN
      SELECT c.relname, c.relkind
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'curated_social'
        AND c.relname NOT IN (  -- HOLD BACK: external late-binding views depend on these (from Step 1b)
          -- production curated_* dependents
          'weekly_primary','dashboard_weekly','post_metrics','daily_primary_paid',
          'int_weekly_cross_channel_stage','int_weekly_kpi','int_daily_kpi_social_player',
          'int_post_metrics_metadata','int_weekly_kpi_social_trn_factors',
          'int_weekly_social_franchise','int_weekly_social_player'
          -- (6 objects referenced only by dbt_morganteisman / dbt_pgat_kevinrussell sandbox
          --  views were removed from this list: OK to break per owner)
        )
        AND c.relname IN (
  'daily_primary',
  'daily_primary_paid',
  'daily_social_player',
  'dashboard_weekly',
  'dashboard_weekly_player_social',
  'dashboard_weekly_social_post_player',
  'dashboard_weekly_social_post_player_v2',
  'int_daily_primary',
  'int_metadata_v2',
  'int_mt_sprout_weekly_media_player',
  'int_weekly_cross_channel_stage',
  'int_weekly_primary',
  'int_weekly_social_player_agg_v2',
  'int_weekly_social_player_v2',
  'int_weekly_social_post_player_sprout',
  'int_weekly_social_post_player_v2',
  'monthly_kpi_mvp_index',
  'post_metadata_v2',
  'post_metrics',
  'post_metrics_metadata_sprout',
  'post_metrics_metadata_sprout_updated',
  'post_metrics_metadata_v2',
  'post_metrics_old',
  'post_metrics_updated',
  'post_metrics_v2',
  'weekly_primary',
  'int_ad_account_post_level_facebook',
  'int_ad_account_post_level_instagram',
  'int_ad_account_post_level_twitter',
  'int_ad_account_post_metrics',
  'int_daily_engagement_rate_backfill',
  'int_daily_kpi_social_player',
  'int_daily_metrics',
  'int_daily_primary_ig_collabs',
  'int_daily_primary_paid',
  'int_daily_primary_update',
  'int_daily_primary_v2',
  'int_daily_social_player',
  'int_daily_social_player_agg',
  'int_daily_social_player_stage',
  'int_date_level_tiktok',
  'int_date_level_tiktok_v2',
  'int_date_level_youtube',
  'int_date_level_youtube_v2',
  'int_facebook_metadata_pgatour',
  'int_facebook_metadata_pgatour_sprout',
  'int_facebook_metadata_pgatour_sprout_updated',
  'int_instagram_metadata_pgatour',
  'int_instagram_metadata_pgatour_sprout',
  'int_instagram_metadata_pgatour_sprout_updated',
  'int_metadata',
  'int_metadata_contentpillar_v2',
  'int_metadata_facebook_v2',
  'int_metadata_formatted',
  'int_metadata_franchises_v2',
  'int_metadata_instagram_v2',
  'int_metadata_pgatour',
  'int_metadata_pgatour_facebook_sprout_updated',
  'int_metadata_pgatour_historical',
  'int_metadata_pgatour_instagram_sprout_updated',
  'int_metadata_pgatour_sprout',
  'int_metadata_pgatour_sprout_updated',
  'int_metadata_pgatour_tiktok_sprout_updated',
  'int_metadata_pgatour_x_sprout_updated',
  'int_metadata_pgatour_youtube_sprout_updated',
  'int_metadata_tiktok_v2',
  'int_metadata_trackingtags_v2',
  'int_metadata_x_v2',
  'int_metadata_youtube_v2',
  'int_post_level_facebook',
  'int_post_level_facebook_updated',
  'int_post_level_facebook_v2',
  'int_post_level_instagram',
  'int_post_level_instagram_collab',
  'int_post_level_instagram_collab_v2',
  'int_post_level_instagram_v2',
  'int_post_level_tiktok',
  'int_post_level_tiktok_v2',
  'int_post_level_twitter',
  'int_post_level_x_v2',
  'int_post_level_youtube_v2',
  'int_post_metrics',
  'int_post_metrics_metadata',
  'int_post_metrics_metadata_sprout',
  'int_post_metrics_metadata_sprout_new',
  'int_post_metrics_metadata_sprout_updated',
  'int_post_metrics_test',
  'int_post_metrics_test_v2',
  'int_post_metrics_updated',
  'int_social_metadata',
  'int_sprout_tags',
  'int_tiktok_metadata_pgatour',
  'int_tiktok_metadata_pgatour_sprout',
  'int_tiktok_metadata_pgatour_sprout_updated',
  'int_weekly_cross_channel',
  'int_weekly_kpi',
  'int_weekly_kpi_social_player',
  'int_weekly_kpi_social_player_v2',
  'int_weekly_kpi_social_trn_factors',
  'int_weekly_kpi_stage',
  'int_weekly_kpi_trn_factors',
  'int_weekly_primary_historical',
  'int_weekly_primary_yt',
  'int_weekly_social_franchise',
  'int_weekly_social_player',
  'int_weekly_social_player_agg',
  'int_weekly_social_player_stage',
  'int_weekly_social_player_stage_v2',
  'int_weekly_social_post_player',
  'int_weekly_social_post_type',
  'int_x_metadata_pgatour',
  'int_x_metadata_pgatour_sprout',
  'int_x_metadata_pgatour_sprout_updated',
  'int_youtube_metadata_pgatour_sprout',
  'int_youtube_metadata_pgatour_sprout_updated'
        )
    LOOP
      ddl_type := CASE r.relkind WHEN 'v' THEN 'VIEW'
                                 WHEN 'm' THEN 'MATERIALIZED VIEW'
                                 ELSE 'TABLE' END;
      BEGIN
        EXECUTE 'DROP ' || ddl_type || ' pgat.curated_social.' || quote_ident(r.relname);
        INSERT INTO drop_log VALUES (r.relname, ddl_type, getdate());
        progress := progress + 1;
      EXCEPTION WHEN OTHERS THEN
        NULL;  -- blocked this pass; may succeed after its dependents are dropped
      END;
    END LOOP;
    IF progress = 0 THEN
      EXIT;
    END IF;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

CALL public.sp_drop_curated_social_list();

-- ---------- STEP 3: what got dropped
SELECT obj_type, COUNT(*) AS dropped FROM drop_log GROUP BY 1;
SELECT * FROM drop_log ORDER by obj_type, obj_name;

-- ---------- STEP 4: what is left and what is blocking it
-- One row per (blocked object, dependent). dependent_in_list = 'Y' means the
-- dependent is itself a list object that was also blocked (chain/cycle).
-- 'N' rows are the external objects the end user needs to approve.
-- dependent_is_dbt_sandbox = 'Y' rows are dbt_* dev schemas: per owner these can be ignored,
-- but an early-binding dbt_* view WILL block the drop until that view is dropped.
SELECT src.relname AS blocked_object,
       CASE src.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view' ELSE 'table' END AS blocked_type,
       dep_ns.nspname || '.' || dep_obj.relname AS dependent_object,
       CASE dep_obj.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view' ELSE 'table' END AS dependent_type,
       CASE WHEN dep_ns.nspname = 'curated_social' AND dep_obj.relname IN (
  'daily_primary',
  'daily_primary_paid',
  'daily_social_player',
  'dashboard_weekly',
  'dashboard_weekly_player_social',
  'dashboard_weekly_social_post_player',
  'dashboard_weekly_social_post_player_v2',
  'int_daily_primary',
  'int_metadata_v2',
  'int_mt_sprout_weekly_media_player',
  'int_weekly_cross_channel_stage',
  'int_weekly_primary',
  'int_weekly_social_player_agg_v2',
  'int_weekly_social_player_v2',
  'int_weekly_social_post_player_sprout',
  'int_weekly_social_post_player_v2',
  'monthly_kpi_mvp_index',
  'post_metadata_v2',
  'post_metrics',
  'post_metrics_metadata_sprout',
  'post_metrics_metadata_sprout_updated',
  'post_metrics_metadata_v2',
  'post_metrics_old',
  'post_metrics_updated',
  'post_metrics_v2',
  'weekly_primary',
  'int_ad_account_post_level_facebook',
  'int_ad_account_post_level_instagram',
  'int_ad_account_post_level_twitter',
  'int_ad_account_post_metrics',
  'int_daily_engagement_rate_backfill',
  'int_daily_kpi_social_player',
  'int_daily_metrics',
  'int_daily_primary_ig_collabs',
  'int_daily_primary_paid',
  'int_daily_primary_update',
  'int_daily_primary_v2',
  'int_daily_social_player',
  'int_daily_social_player_agg',
  'int_daily_social_player_stage',
  'int_date_level_tiktok',
  'int_date_level_tiktok_v2',
  'int_date_level_youtube',
  'int_date_level_youtube_v2',
  'int_facebook_metadata_pgatour',
  'int_facebook_metadata_pgatour_sprout',
  'int_facebook_metadata_pgatour_sprout_updated',
  'int_instagram_metadata_pgatour',
  'int_instagram_metadata_pgatour_sprout',
  'int_instagram_metadata_pgatour_sprout_updated',
  'int_metadata',
  'int_metadata_contentpillar_v2',
  'int_metadata_facebook_v2',
  'int_metadata_formatted',
  'int_metadata_franchises_v2',
  'int_metadata_instagram_v2',
  'int_metadata_pgatour',
  'int_metadata_pgatour_facebook_sprout_updated',
  'int_metadata_pgatour_historical',
  'int_metadata_pgatour_instagram_sprout_updated',
  'int_metadata_pgatour_sprout',
  'int_metadata_pgatour_sprout_updated',
  'int_metadata_pgatour_tiktok_sprout_updated',
  'int_metadata_pgatour_x_sprout_updated',
  'int_metadata_pgatour_youtube_sprout_updated',
  'int_metadata_tiktok_v2',
  'int_metadata_trackingtags_v2',
  'int_metadata_x_v2',
  'int_metadata_youtube_v2',
  'int_post_level_facebook',
  'int_post_level_facebook_updated',
  'int_post_level_facebook_v2',
  'int_post_level_instagram',
  'int_post_level_instagram_collab',
  'int_post_level_instagram_collab_v2',
  'int_post_level_instagram_v2',
  'int_post_level_tiktok',
  'int_post_level_tiktok_v2',
  'int_post_level_twitter',
  'int_post_level_x_v2',
  'int_post_level_youtube_v2',
  'int_post_metrics',
  'int_post_metrics_metadata',
  'int_post_metrics_metadata_sprout',
  'int_post_metrics_metadata_sprout_new',
  'int_post_metrics_metadata_sprout_updated',
  'int_post_metrics_test',
  'int_post_metrics_test_v2',
  'int_post_metrics_updated',
  'int_social_metadata',
  'int_sprout_tags',
  'int_tiktok_metadata_pgatour',
  'int_tiktok_metadata_pgatour_sprout',
  'int_tiktok_metadata_pgatour_sprout_updated',
  'int_weekly_cross_channel',
  'int_weekly_kpi',
  'int_weekly_kpi_social_player',
  'int_weekly_kpi_social_player_v2',
  'int_weekly_kpi_social_trn_factors',
  'int_weekly_kpi_stage',
  'int_weekly_kpi_trn_factors',
  'int_weekly_primary_historical',
  'int_weekly_primary_yt',
  'int_weekly_social_franchise',
  'int_weekly_social_player',
  'int_weekly_social_player_agg',
  'int_weekly_social_player_stage',
  'int_weekly_social_player_stage_v2',
  'int_weekly_social_post_player',
  'int_weekly_social_post_type',
  'int_x_metadata_pgatour',
  'int_x_metadata_pgatour_sprout',
  'int_x_metadata_pgatour_sprout_updated',
  'int_youtube_metadata_pgatour_sprout',
  'int_youtube_metadata_pgatour_sprout_updated'
       ) THEN 'Y' ELSE 'N' END AS dependent_in_list,
       CASE WHEN dep_ns.nspname LIKE 'dbt%' THEN 'Y' ELSE 'N' END AS dependent_is_dbt_sandbox
FROM pg_class src
JOIN pg_namespace src_ns ON src_ns.oid = src.relnamespace AND src_ns.nspname = 'curated_social'
JOIN pg_depend d         ON d.refobjid = src.oid
JOIN pg_rewrite r        ON d.objid = r.oid
JOIN pg_class dep_obj    ON r.ev_class = dep_obj.oid
JOIN pg_namespace dep_ns ON dep_ns.oid = dep_obj.relnamespace
WHERE dep_obj.oid <> src.oid
  AND src.relname IN (
  'daily_primary',
  'daily_primary_paid',
  'daily_social_player',
  'dashboard_weekly',
  'dashboard_weekly_player_social',
  'dashboard_weekly_social_post_player',
  'dashboard_weekly_social_post_player_v2',
  'int_daily_primary',
  'int_metadata_v2',
  'int_mt_sprout_weekly_media_player',
  'int_weekly_cross_channel_stage',
  'int_weekly_primary',
  'int_weekly_social_player_agg_v2',
  'int_weekly_social_player_v2',
  'int_weekly_social_post_player_sprout',
  'int_weekly_social_post_player_v2',
  'monthly_kpi_mvp_index',
  'post_metadata_v2',
  'post_metrics',
  'post_metrics_metadata_sprout',
  'post_metrics_metadata_sprout_updated',
  'post_metrics_metadata_v2',
  'post_metrics_old',
  'post_metrics_updated',
  'post_metrics_v2',
  'weekly_primary',
  'int_ad_account_post_level_facebook',
  'int_ad_account_post_level_instagram',
  'int_ad_account_post_level_twitter',
  'int_ad_account_post_metrics',
  'int_daily_engagement_rate_backfill',
  'int_daily_kpi_social_player',
  'int_daily_metrics',
  'int_daily_primary_ig_collabs',
  'int_daily_primary_paid',
  'int_daily_primary_update',
  'int_daily_primary_v2',
  'int_daily_social_player',
  'int_daily_social_player_agg',
  'int_daily_social_player_stage',
  'int_date_level_tiktok',
  'int_date_level_tiktok_v2',
  'int_date_level_youtube',
  'int_date_level_youtube_v2',
  'int_facebook_metadata_pgatour',
  'int_facebook_metadata_pgatour_sprout',
  'int_facebook_metadata_pgatour_sprout_updated',
  'int_instagram_metadata_pgatour',
  'int_instagram_metadata_pgatour_sprout',
  'int_instagram_metadata_pgatour_sprout_updated',
  'int_metadata',
  'int_metadata_contentpillar_v2',
  'int_metadata_facebook_v2',
  'int_metadata_formatted',
  'int_metadata_franchises_v2',
  'int_metadata_instagram_v2',
  'int_metadata_pgatour',
  'int_metadata_pgatour_facebook_sprout_updated',
  'int_metadata_pgatour_historical',
  'int_metadata_pgatour_instagram_sprout_updated',
  'int_metadata_pgatour_sprout',
  'int_metadata_pgatour_sprout_updated',
  'int_metadata_pgatour_tiktok_sprout_updated',
  'int_metadata_pgatour_x_sprout_updated',
  'int_metadata_pgatour_youtube_sprout_updated',
  'int_metadata_tiktok_v2',
  'int_metadata_trackingtags_v2',
  'int_metadata_x_v2',
  'int_metadata_youtube_v2',
  'int_post_level_facebook',
  'int_post_level_facebook_updated',
  'int_post_level_facebook_v2',
  'int_post_level_instagram',
  'int_post_level_instagram_collab',
  'int_post_level_instagram_collab_v2',
  'int_post_level_instagram_v2',
  'int_post_level_tiktok',
  'int_post_level_tiktok_v2',
  'int_post_level_twitter',
  'int_post_level_x_v2',
  'int_post_level_youtube_v2',
  'int_post_metrics',
  'int_post_metrics_metadata',
  'int_post_metrics_metadata_sprout',
  'int_post_metrics_metadata_sprout_new',
  'int_post_metrics_metadata_sprout_updated',
  'int_post_metrics_test',
  'int_post_metrics_test_v2',
  'int_post_metrics_updated',
  'int_social_metadata',
  'int_sprout_tags',
  'int_tiktok_metadata_pgatour',
  'int_tiktok_metadata_pgatour_sprout',
  'int_tiktok_metadata_pgatour_sprout_updated',
  'int_weekly_cross_channel',
  'int_weekly_kpi',
  'int_weekly_kpi_social_player',
  'int_weekly_kpi_social_player_v2',
  'int_weekly_kpi_social_trn_factors',
  'int_weekly_kpi_stage',
  'int_weekly_kpi_trn_factors',
  'int_weekly_primary_historical',
  'int_weekly_primary_yt',
  'int_weekly_social_franchise',
  'int_weekly_social_player',
  'int_weekly_social_player_agg',
  'int_weekly_social_player_stage',
  'int_weekly_social_player_stage_v2',
  'int_weekly_social_post_player',
  'int_weekly_social_post_type',
  'int_x_metadata_pgatour',
  'int_x_metadata_pgatour_sprout',
  'int_x_metadata_pgatour_sprout_updated',
  'int_youtube_metadata_pgatour_sprout',
  'int_youtube_metadata_pgatour_sprout_updated'
  )
UNION ALL
SELECT src.relname, 'table',
       fk_ns.nspname || '.' || fk_t.relname || ' (FK ' || c.conname || ')', 'table', 'N', 'N'
FROM pg_class src
JOIN pg_namespace ns ON ns.oid = src.relnamespace AND ns.nspname = 'curated_social'
JOIN pg_constraint c ON c.confrelid = src.oid AND c.contype = 'f'
JOIN pg_class fk_t ON fk_t.oid = c.conrelid
JOIN pg_namespace fk_ns ON fk_ns.oid = fk_t.relnamespace
WHERE src.relname IN (
  'daily_primary',
  'daily_primary_paid',
  'daily_social_player',
  'dashboard_weekly',
  'dashboard_weekly_player_social',
  'dashboard_weekly_social_post_player',
  'dashboard_weekly_social_post_player_v2',
  'int_daily_primary',
  'int_metadata_v2',
  'int_mt_sprout_weekly_media_player',
  'int_weekly_cross_channel_stage',
  'int_weekly_primary',
  'int_weekly_social_player_agg_v2',
  'int_weekly_social_player_v2',
  'int_weekly_social_post_player_sprout',
  'int_weekly_social_post_player_v2',
  'monthly_kpi_mvp_index',
  'post_metadata_v2',
  'post_metrics',
  'post_metrics_metadata_sprout',
  'post_metrics_metadata_sprout_updated',
  'post_metrics_metadata_v2',
  'post_metrics_old',
  'post_metrics_updated',
  'post_metrics_v2',
  'weekly_primary',
  'int_ad_account_post_level_facebook',
  'int_ad_account_post_level_instagram',
  'int_ad_account_post_level_twitter',
  'int_ad_account_post_metrics',
  'int_daily_engagement_rate_backfill',
  'int_daily_kpi_social_player',
  'int_daily_metrics',
  'int_daily_primary_ig_collabs',
  'int_daily_primary_paid',
  'int_daily_primary_update',
  'int_daily_primary_v2',
  'int_daily_social_player',
  'int_daily_social_player_agg',
  'int_daily_social_player_stage',
  'int_date_level_tiktok',
  'int_date_level_tiktok_v2',
  'int_date_level_youtube',
  'int_date_level_youtube_v2',
  'int_facebook_metadata_pgatour',
  'int_facebook_metadata_pgatour_sprout',
  'int_facebook_metadata_pgatour_sprout_updated',
  'int_instagram_metadata_pgatour',
  'int_instagram_metadata_pgatour_sprout',
  'int_instagram_metadata_pgatour_sprout_updated',
  'int_metadata',
  'int_metadata_contentpillar_v2',
  'int_metadata_facebook_v2',
  'int_metadata_formatted',
  'int_metadata_franchises_v2',
  'int_metadata_instagram_v2',
  'int_metadata_pgatour',
  'int_metadata_pgatour_facebook_sprout_updated',
  'int_metadata_pgatour_historical',
  'int_metadata_pgatour_instagram_sprout_updated',
  'int_metadata_pgatour_sprout',
  'int_metadata_pgatour_sprout_updated',
  'int_metadata_pgatour_tiktok_sprout_updated',
  'int_metadata_pgatour_x_sprout_updated',
  'int_metadata_pgatour_youtube_sprout_updated',
  'int_metadata_tiktok_v2',
  'int_metadata_trackingtags_v2',
  'int_metadata_x_v2',
  'int_metadata_youtube_v2',
  'int_post_level_facebook',
  'int_post_level_facebook_updated',
  'int_post_level_facebook_v2',
  'int_post_level_instagram',
  'int_post_level_instagram_collab',
  'int_post_level_instagram_collab_v2',
  'int_post_level_instagram_v2',
  'int_post_level_tiktok',
  'int_post_level_tiktok_v2',
  'int_post_level_twitter',
  'int_post_level_x_v2',
  'int_post_level_youtube_v2',
  'int_post_metrics',
  'int_post_metrics_metadata',
  'int_post_metrics_metadata_sprout',
  'int_post_metrics_metadata_sprout_new',
  'int_post_metrics_metadata_sprout_updated',
  'int_post_metrics_test',
  'int_post_metrics_test_v2',
  'int_post_metrics_updated',
  'int_social_metadata',
  'int_sprout_tags',
  'int_tiktok_metadata_pgatour',
  'int_tiktok_metadata_pgatour_sprout',
  'int_tiktok_metadata_pgatour_sprout_updated',
  'int_weekly_cross_channel',
  'int_weekly_kpi',
  'int_weekly_kpi_social_player',
  'int_weekly_kpi_social_player_v2',
  'int_weekly_kpi_social_trn_factors',
  'int_weekly_kpi_stage',
  'int_weekly_kpi_trn_factors',
  'int_weekly_primary_historical',
  'int_weekly_primary_yt',
  'int_weekly_social_franchise',
  'int_weekly_social_player',
  'int_weekly_social_player_agg',
  'int_weekly_social_player_stage',
  'int_weekly_social_player_stage_v2',
  'int_weekly_social_post_player',
  'int_weekly_social_post_type',
  'int_x_metadata_pgatour',
  'int_x_metadata_pgatour_sprout',
  'int_x_metadata_pgatour_sprout_updated',
  'int_youtube_metadata_pgatour_sprout',
  'int_youtube_metadata_pgatour_sprout_updated'
  )
ORDER BY 1, 3;

-- ---------- STEP 5: list objects that STILL EXIST in curated_social
-- (held back or blocked). A list name missing from both this result and drop_log
-- was already gone before the run (see Step 1a).
SELECT c.relname AS still_exists,
       CASE c.relkind WHEN 'v' THEN 'view' WHEN 'm' THEN 'materialized view' ELSE 'table' END AS obj_type
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace AND n.nspname = 'curated_social'
WHERE c.relname IN (
  'daily_primary',
  'daily_primary_paid',
  'daily_social_player',
  'dashboard_weekly',
  'dashboard_weekly_player_social',
  'dashboard_weekly_social_post_player',
  'dashboard_weekly_social_post_player_v2',
  'int_daily_primary',
  'int_metadata_v2',
  'int_mt_sprout_weekly_media_player',
  'int_weekly_cross_channel_stage',
  'int_weekly_primary',
  'int_weekly_social_player_agg_v2',
  'int_weekly_social_player_v2',
  'int_weekly_social_post_player_sprout',
  'int_weekly_social_post_player_v2',
  'monthly_kpi_mvp_index',
  'post_metadata_v2',
  'post_metrics',
  'post_metrics_metadata_sprout',
  'post_metrics_metadata_sprout_updated',
  'post_metrics_metadata_v2',
  'post_metrics_old',
  'post_metrics_updated',
  'post_metrics_v2',
  'weekly_primary',
  'int_ad_account_post_level_facebook',
  'int_ad_account_post_level_instagram',
  'int_ad_account_post_level_twitter',
  'int_ad_account_post_metrics',
  'int_daily_engagement_rate_backfill',
  'int_daily_kpi_social_player',
  'int_daily_metrics',
  'int_daily_primary_ig_collabs',
  'int_daily_primary_paid',
  'int_daily_primary_update',
  'int_daily_primary_v2',
  'int_daily_social_player',
  'int_daily_social_player_agg',
  'int_daily_social_player_stage',
  'int_date_level_tiktok',
  'int_date_level_tiktok_v2',
  'int_date_level_youtube',
  'int_date_level_youtube_v2',
  'int_facebook_metadata_pgatour',
  'int_facebook_metadata_pgatour_sprout',
  'int_facebook_metadata_pgatour_sprout_updated',
  'int_instagram_metadata_pgatour',
  'int_instagram_metadata_pgatour_sprout',
  'int_instagram_metadata_pgatour_sprout_updated',
  'int_metadata',
  'int_metadata_contentpillar_v2',
  'int_metadata_facebook_v2',
  'int_metadata_formatted',
  'int_metadata_franchises_v2',
  'int_metadata_instagram_v2',
  'int_metadata_pgatour',
  'int_metadata_pgatour_facebook_sprout_updated',
  'int_metadata_pgatour_historical',
  'int_metadata_pgatour_instagram_sprout_updated',
  'int_metadata_pgatour_sprout',
  'int_metadata_pgatour_sprout_updated',
  'int_metadata_pgatour_tiktok_sprout_updated',
  'int_metadata_pgatour_x_sprout_updated',
  'int_metadata_pgatour_youtube_sprout_updated',
  'int_metadata_tiktok_v2',
  'int_metadata_trackingtags_v2',
  'int_metadata_x_v2',
  'int_metadata_youtube_v2',
  'int_post_level_facebook',
  'int_post_level_facebook_updated',
  'int_post_level_facebook_v2',
  'int_post_level_instagram',
  'int_post_level_instagram_collab',
  'int_post_level_instagram_collab_v2',
  'int_post_level_instagram_v2',
  'int_post_level_tiktok',
  'int_post_level_tiktok_v2',
  'int_post_level_twitter',
  'int_post_level_x_v2',
  'int_post_level_youtube_v2',
  'int_post_metrics',
  'int_post_metrics_metadata',
  'int_post_metrics_metadata_sprout',
  'int_post_metrics_metadata_sprout_new',
  'int_post_metrics_metadata_sprout_updated',
  'int_post_metrics_test',
  'int_post_metrics_test_v2',
  'int_post_metrics_updated',
  'int_social_metadata',
  'int_sprout_tags',
  'int_tiktok_metadata_pgatour',
  'int_tiktok_metadata_pgatour_sprout',
  'int_tiktok_metadata_pgatour_sprout_updated',
  'int_weekly_cross_channel',
  'int_weekly_kpi',
  'int_weekly_kpi_social_player',
  'int_weekly_kpi_social_player_v2',
  'int_weekly_kpi_social_trn_factors',
  'int_weekly_kpi_stage',
  'int_weekly_kpi_trn_factors',
  'int_weekly_primary_historical',
  'int_weekly_primary_yt',
  'int_weekly_social_franchise',
  'int_weekly_social_player',
  'int_weekly_social_player_agg',
  'int_weekly_social_player_stage',
  'int_weekly_social_player_stage_v2',
  'int_weekly_social_post_player',
  'int_weekly_social_post_type',
  'int_x_metadata_pgatour',
  'int_x_metadata_pgatour_sprout',
  'int_x_metadata_pgatour_sprout_updated',
  'int_youtube_metadata_pgatour_sprout',
  'int_youtube_metadata_pgatour_sprout_updated'
)
ORDER BY 2, 1;

-- Cleanup (optional)
-- DROP PROCEDURE public.sp_drop_curated_social_list();

-- WEEKLY_PRIMARY
drop view pgat.curated_fan_engagement.int_weekly_media_tragectory_stage; 
drop table pgat.curated_social.weekly_primary;

-- DASHBOARD_WEEKLY
drop view pgat.curated_digital.int_content_kpi_stage;
drop view pgat.curated_fan_engagement.int_champions_tour;
drop table pgat.curated_social.dashboard_weekly;

-- POST_METRICS
drop table pgat.curated_social.post_metrics;

-- DAILY_PRIMARY_PAID
drop table pgat.curated_social.daily_primary_paid;

-- INT_WEEKLY_CROSS_CHANNEL_STAGE
drop view pgat.curated_fan_engagement.int_cross_channel_base_social;
drop table pgat.curated_social.INT_WEEKLY_CROSS_CHANNEL_STAGE;

-- INT_WEEKLY_KPI
drop view pgat.curated_digital.int_drive_goals_stage;
drop view pgat.curated_digital.int_monthly_kpi_cc_stage;
drop view pgat.curated_digital.int_weekly_pm_features;
drop view pgat.curated_social.INT_WEEKLY_KPI;

-- INT_DAILY_KPI_SOCIAL_PLAYER
drop view pgat.curated_social.INT_DAILY_KPI_SOCIAL_PLAYER

-- INT_POST_METRICS_METADATA
drop view pgat.curated_corppart_x.int_trn_reporting_social_metrics;
drop view pgat.curated_social.INT_POST_METRICS_METADATA;

-- INT_WEEKLY_KPI_SOCIAL_TRN_FACTORS
drop view pgat.curated_digital.int_weekly_kpi_content_cross_channel;
drop view pgat.curated_social.INT_WEEKLY_KPI_SOCIAL_TRN_FACTORS;

-- INT_WEEKLY_SOCIAL_FRANCHISE
drop view pgat.curated_digital.int_weekly_kpi_franchise_stage;
drop view pgat.curated_social.INT_WEEKLY_SOCIAL_FRANCHISE

-- INT_WEEKLY_SOCIAL_PLAYER
drop view pgat.curated_digital.int_weekly_kpi_player_stage;
drop view pgat.curated_other.int_weekly_player_fan_engagement;
drop view pgat.curated_social.INT_WEEKLY_SOCIAL_PLAYER
