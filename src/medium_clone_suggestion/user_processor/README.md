/**
 * Fetches user activities by calling an RPC Supabase function 'fetch_user_activities'
 * 
 * The function queries and combines user history and engagement data after a specified cutoff time
 * 
 * Function Definition:
 * - Returns: Table with columns (userid, postid, created_at, segment)
 * - Parameters: cutoff (TIMESTAMPTZ) - Timestamp to filter records after
 * 
 * The returned data combines:
 * 1. History records (segment = NULL)
 * 2. Engagement records (includes segment data)
 * 
 * Both datasets are filtered to only include records after the cutoff timestamp
 */

/*
 * Retrieves user activities by combining history and engagements data for specified users
 * 
 * @param cutoff     - Timestamp threshold to filter activities after this date/time
 * @param user_ids   - Array of user UUIDs to fetch activities for
 * 
 * @returns Table with following columns:
 *  - userid:      UUID of the user
 *  - postid:      UUID of the associated post
 *  - created_at:  Timestamp when the activity occurred
 *  - segment:     Segment number (NULL for history records, populated for engagements)
 *
 * The function combines:
 * 1. History records after cutoff for specified users
 * 2. Engagement records after cutoff for specified users
 * Results are unified using UNION ALL
 */