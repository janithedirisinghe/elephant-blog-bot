# Bot Article Creation & Admin Approval Workflow

This document outlines the multi-agent (bot) article submission flow for the Tuskers Blog Backend. Bot-created articles are saved as **pending** and only appear on the public blog after an admin approves them.

## Overview

```
Bot (x-api-key) ──POST /articles/bot──▶ Article saved as PENDING
                                              │
                                              ▼
                              Admin reviews via /admin/articles
                                   │                    │
                            PATCH :id/approve     PATCH :id/reject
                                   │                    │
                                   ▼                    ▼
                        Visible on blog website    Stays hidden
```

Public fetch endpoints only return **approved** articles (and legacy articles created before this feature). Pending and rejected articles are never exposed to the blog website or the sitemap.

## Schema Changes

The `Article` schema has three new fields. All have defaults, so **existing articles are unaffected and no migration is needed**:

```typescript
@Prop({ default: 'standard' })
articleType: string;

@Prop({ type: String, enum: ArticleStatus, default: ArticleStatus.Approved })
publishedStatus: ArticleStatus; // 'pending' | 'approved' | 'rejected'

@Prop({ default: false })
botCreated: boolean;
```

- `articleType` — type/category of the article (e.g. bot pipeline type). Defaults to `standard`.
- `publishedStatus` — moderation status. Defaults to `approved` so articles created by the admin panel publish immediately, exactly as before.
- `botCreated` — `true` only for articles submitted through the bot endpoint.

### Backward compatibility

Public queries filter with:

```typescript
{ publishedStatus: { $nin: ['pending', 'rejected'] } }
```

Documents created before this feature have no `publishedStatus` field at all — `$nin` still matches them, so all existing articles remain visible without any data migration.

## Bot Endpoint

### `POST /articles/bot`

Creates an article in **pending** status. Used by the multi-agent article creation bot only.

**Authentication:** API key in the `x-api-key` header, validated against the `BOT_API_KEY` environment variable (see [Configuration](#configuration)). Implemented in `src/auth/bot-api-key.guard.ts`. Requests with a missing or wrong key get `401 Unauthorized`.

**Request body** (same as a normal article, plus optional `articleType`):

```json
{
  "title": "The Majestic Tuskers of Yala",
  "excerpt": "A short summary...",
  "content": "<p>Full article HTML/markdown...</p>",
  "category": "Wildlife",
  "tags": ["tuskers", "yala"],
  "author": "Tusker AI Bot",
  "publishDate": "2026-06-11",
  "images": ["https://example.com/image.jpg"],
  "slug": "optional-custom-slug",
  "articleType": "ai-generated"
}
```

**Example:**

```bash
curl -X POST https://<api-host>/articles/bot \
  -H "Content-Type: application/json" \
  -H "x-api-key: <BOT_API_KEY>" \
  -d '{ "title": "...", "excerpt": "...", "content": "...", "category": "...", "author": "...", "publishDate": "2026-06-11" }'
```

**Server-enforced behavior** (cannot be overridden by the request body):

- `publishedStatus` is forced to `pending`
- `botCreated` is forced to `true`
- `slug` is auto-generated from the title if not provided, and uniqueness is checked against **all** articles (including pending ones)
- Body is validated with a whitelist `ValidationPipe` — unknown fields are rejected

## Admin Moderation Endpoints

All routes require a valid admin JWT (`JwtAuthGuard` + `AdminRoleGuard`), same as the sightings admin routes. Implemented in `src/article/admin-article.controller.ts`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/articles` | All articles. Optional `?status=pending\|approved\|rejected` filter |
| GET | `/admin/articles/pending` | Articles awaiting review |
| GET | `/admin/articles/approved` | Approved articles |
| GET | `/admin/articles/rejected` | Rejected articles |
| GET | `/admin/articles/:id` | Single article regardless of status (use this to preview/edit pending articles) |
| PATCH | `/admin/articles/:id/approve` | Approve — article immediately appears on the blog like any other |
| PATCH | `/admin/articles/:id/reject` | Reject — article stays hidden |

To edit a pending article before approving, fetch it with `GET /admin/articles/:id` and update it with the existing `PUT /articles/:id` (which works on any status).

## Public Endpoint Behavior

All public fetches in `src/article/article.service.ts` now exclude pending and rejected articles:

- `GET /articles`
- `GET /articles/recent`
- `GET /articles/category/:category`
- `GET /articles/tag/:tag`
- `GET /articles/search?q=`
- `GET /articles/tags/all` (tags from hidden articles are not listed)
- `GET /articles/slug/:slug` (returns `404` for pending/rejected)
- `GET /articles/:id` (returns `404` for pending/rejected)

The sitemap (`/sitemap.xml`) uses the same filtered query, so pending articles never appear in it.

Unchanged endpoints: `POST /articles`, `PUT /articles/:id`, `DELETE /articles/:id` (admin JWT, as before). Articles created via `POST /articles` default to `approved`, so the existing admin panel flow is unaffected.

## Configuration

Add the bot API key to the environment:

```
BOT_API_KEY=<long-random-secret>
```

- Already added to the local `.env`
- **Must also be added to the Azure App Service application settings** for production
- Share the value only with the article-creation bot; rotate it by changing the env value and updating the bot

## Files Added / Changed

| File | Change |
|------|--------|
| `src/article/enums/article.enums.ts` | New — `ArticleStatus` enum |
| `src/article/entities/article.entity.ts` | Added `articleType`, `publishedStatus`, `botCreated` |
| `src/article/dto/create-article.dto.ts` | Added optional `articleType` |
| `src/article/dto/create-bot-article.dto.ts` | New — DTO for the bot endpoint |
| `src/auth/bot-api-key.guard.ts` | New — `x-api-key` guard for the bot |
| `src/article/article.controller.ts` | Added `POST /articles/bot` |
| `src/article/admin-article.controller.ts` | New — admin moderation routes |
| `src/article/article.service.ts` | Public-query filtering, bot create, approve/reject methods |
| `src/article/article.module.ts` | Registered `AdminArticleController` |
