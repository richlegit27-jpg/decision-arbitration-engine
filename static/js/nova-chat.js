/*
 * NOVA_LEGACY_SEND_DISABLED_20260829
 *
 * Desktop message sending is owned exclusively by:
 *
 *     static/js/composer-actions.js
 *
 * This legacy file previously attached its own:
 *     sendBtn click handler
 *     Enter key handler
 *
 * Those handlers caused competing send pipelines.
 */
