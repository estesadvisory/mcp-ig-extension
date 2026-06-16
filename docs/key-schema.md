# IG Monitor Key Schema

Metrics written by `mcp-ig-extension` use dot-notation keys under the `ig_monitor.` namespace in the deployed grok-memory-mcp server.

## Per-media insights

Default key for posts and generic media:

```
ig_monitor.media.{media_id}.insights
```

Reels:

```
ig_monitor.accounts.{ig_user_id}.reels.{media_id}.insights
```

Stories:

```
ig_monitor.accounts.{ig_user_id}.stories.{media_id}.insights
```

## Account daily rollup (planned)

```
ig_monitor.accounts.{ig_user_id}.daily.{YYYYMMDD}.summary
```

## Value shape

```json
{
  "ig_user_id": "17841400000000000",
  "media_id": "18000000000000000",
  "media_type": "REEL",
  "timestamp": "2026-06-14T12:34:56+0000",
  "permalink": "https://www.instagram.com/reel/...",
  "metrics": {
    "impressions": 12345,
    "reach": 9876,
    "engagement": 234,
    "likes": 150,
    "comments": 12,
    "shares": 5,
    "saves": 45,
    "video_views": 8900
  },
  "collected_at": "2026-06-15T18:03:00Z",
  "source": "ig-mcp-extension",
  "run_id": "evt-abc123"
}
```

## MCP write transport

v1 uses the canonical `store` tool payload over the MCP Streamable HTTP endpoint:

- `logical_key` — one of the keys above
- `content` — JSON string of the value shape
- `metadata.title` / `metadata.summary` — short strings for vector search
- `Authorization: Bearer <token>` — from AWS Secrets Manager

Exact HTTP framing may evolve once the deployed MCP adds a dedicated authenticated write path; the key and value contract stays the same.