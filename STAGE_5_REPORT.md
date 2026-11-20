# Stage 5 — AI Business Assistant

## Status

Stage 5 implementation is present in the local project: a read-only assistant UI, tenant-scoped conversation storage, deterministic business-context retrieval, usage accounting and a configurable backend provider adapter are implemented.

The real instructor AI provider is **not claimed active** because provider API documentation and credentials were not supplied. No provider key was added or committed.

## Features implemented

- Persistent AI conversations and messages owned by a user and business.
- New, continue, retrieve, rename and delete conversation operations.
- Read-only chat interface with suggested questions, loading, typing, error, retry and usage display.
- Mobile-responsive conversation layout.
- Backend-only provider adapter with configurable base URL, model, format, chat path, authorization scheme and timeout.
- Missing/invalid provider configuration returns explicit `503` responses.
- Deterministic, tenant-scoped context for:
  - period financial summary;
  - best-selling and profitable products;
  - low-stock and out-of-stock products;
  - expense categories;
  - inventory units;
  - outstanding customer balances.
- Direct insights and reports endpoints do not require an AI provider call.
- Successful-reply usage records, monthly period boundaries, default plan limits and idempotent request handling.
- Future plan compatibility for Starter 100, Growth 500 and Business 1,500 replies.
- Chat is read-only and cannot execute database mutations.

## Provider configuration

Set values only in the ignored `backend/.env`:

```text
AI_API_KEY=
AI_BASE_URL=
AI_MODEL=
AI_API_FORMAT=openai_chat
AI_CHAT_PATH=/chat/completions
AI_AUTH_SCHEME=Bearer
AI_TIMEOUT_SECONDS=30
AI_MAX_CONTEXT_MESSAGES=12
AI_DEFAULT_PLAN_KEY=starter
AI_DEFAULT_PLAN_LIMIT=100
AI_STARTER_LIMIT=100
AI_GROWTH_LIMIT=500
AI_BUSINESS_LIMIT=1500
```

Supported formats are not assumed to be valid for a real provider:

- `AI_API_FORMAT=openai_chat` sends an OpenAI-style chat-completions payload and parses `choices[0].message.content`.
- Other values use a generic model/messages payload and flexible content parsing (`response`, `answer`, `content`, `output_text`, or choices).

Before activation, instructor documentation must confirm the base URL, authentication header, model, path, request and response formats, streaming behavior and rate limits.

## Database

Migration `d5f61b0a2c44` adds:

- `ai_conversations`
- `ai_messages`
- `ai_usage_records`

It follows `c51d47a9291f`. The local SQLite database was backed up before upgrade at:

`backend\instance\don_prosy.db.stage5-20261117.bak`

## Verification

- Backend: **46 tests passed** after adding focused provider timeout/HTTP error coverage.
- Frontend: production build passed.
- Migration head: `d5f61b0a2c44`.
- Local migration check: no model/migration differences after upgrade.
- Mock AI chat, missing provider, usage, idempotency, conversation ownership and tenant isolation tests pass.
- Provider timeout, HTTP error parsing and real provider response behavior remain untested against an external service.

## Security

- API key remains server-side.
- Every chat/conversation operation requires an authenticated active business membership.
- Conversation reads, updates and deletes are restricted to the same user and business.
- The context builder only performs read queries scoped by `business_id`.
- The model receives data only in the prompt and has no SQL or mutation tool.
- User input is bounded and history/context length is limited.
- CSRF applies to mutations.
- Successful provider replies only increase usage; failed provider requests do not.
- Idempotency request IDs prevent duplicate provider calls and assistant usage within a conversation.

## Remaining work

- Obtain and verify actual instructor provider documentation and credentials.
- Test real response, timeout and rate-limit behavior.
- Add future subscription-plan selection instead of the environment default.
- Add provider token/cost metadata if the actual provider exposes it.
- Complete browser-driven chat history/mobile and accessibility tests.
- Complete PostgreSQL migration verification and production configuration.
