# Watch Yo Mouf

Dedicated Discord voice-safety companion for [Dank Shield](https://github.com/UglyGameFace/Dank-Shield).

**Status:** The independent Discord gateway has passed a live `/watchyo` command response on Android. The DAVE decoder prerequisite checks have passed CI on PR #2, which is merged. The authenticated private bridge has been verified live. A read-only member eligibility client is now staged in a paired draft. **Audio receive, transcription, moderation, and cross-bot control-plane integration are not implemented or enabled in this companion.**

## Mission

Support configurable, **consented** voice conduct review without burdening the main Dank Shield process. Distinguish harmful conduct (unwanted sexual remarks, graphic harassment, threats, targeted abuse) from ordinary discussion of identity, relationships, education, quotations, and gaming banter. LGBTQ+ identity must never itself be classified as misconduct.

Source requirements: [Dank Shield voice-safety issue #517](https://github.com/UglyGameFace/Dank-Shield/issues/517). Treat that issue as the authoritative *product brief*, but trace current running code and deployment config before extracting or replacing any implementation.

## Intended ownership boundaries

| Component | Authority |
| --- | --- |
| Dank Shield control plane | Guild settings, staff UI, verified **voice-specific** consent/withdrawal record, policy versions, and human incident review |
| Watch Yo Mouf Discord application | Its own bot token, installed-guild membership, DAVE voice connection, per-speaker receive, speaker/VC lifecycle, bounded capture buffers |
| Voice processing workers | Bounded STT + context-sensitive classifier, quotas, no automatic bans |
| Authenticated incident channel | Minimal decision metadata returned to Dank Shield; no general audio archives |

Exactly **one** effective receiver may own a guild's monitored room at a time. On migration, disable the equivalent in-process Dank Shield receiver for that guild and provide a tested rollback path.

## Required safety gates before opening a microphone

1. Guild staff deliberately configure and enable one monitored voice room (initial scope), with visible member notice and appropriate legal/privacy review.
2. The member has a **versioned, explicit, voice-specific** agreement accepted through a properly disclosed flow. A Verified role, ordinary rules acceptance, or old Live Captions consent is **not** sufficient by itself.
3. An opt-out immediately withdraws audio admission. An unverified consent read, failed revocation persistence, missing bot permissions, absent provider approval, or DAVE failure must **fail closed**.
4. No hidden recordings, no broad transcript or raw-audio logs, no automatic severe punishment, no guessing speaker attribution from mixed audio.
5. Monitoring state shown to staff must reflect actual receiver/provider readiness: `off`, `starting`, `on`, or `degraded`.

## Required implementation path (one active task at a time)

1. Verify current source branch and deployed build of Dank Shield; locate the authoritative `CommunityVoiceCaptionManager`, agreement storage, session ownership, selectors and alert contract. Do not blindly copy old code or stack two voice listeners.
2. Validate a maintained **DAVE-capable receive stack** against Discord's current encrypted voice behavior on consented test calls. Verify actual decoded per-speaker audio (including joins/leaves, reconnect, overlapping talk and rekeys), not merely successful voice connection.
3. Implement a standalone gateway worker with minimal privileges, bounded buffers, per-guild session leases/fencing, resource caps and clean shutdown. No cross-host SQLite assumption.
4. Implement signed, versioned Dank Shield → Watch Yo Mouf control messages and consent/revocation propagation; enforce revocation at audio processing, even across reconnects or stale leases.
5. Integrate replaceable transcription and conduct classification with calibrated confidence and abstention. Gemini use requires explicit billing/data-handling, age eligibility and consent review; API key presence is **not** provider readiness.
6. Return minimal structured incidents for private staff review. Include appeals/overrides and moderator-triggered incident reporting. A transcript snippet requires appropriate consent and controlled retention.
7. Implement diagnostics, error telemetry without speech content, graceful degradation, Android moderation UI checks, Discloud deployment, and gradual rollout.

## Scalability contract

10,000+ **installed guilds** is a design target, **not** a tested concurrent voice capacity. Gateway shard count, voice channels, concurrent speakers, CPU/RAM, queue latency, voice-hour costs, provider quotas, and failure isolation must all be measured. Start with a small consented canary and load-test 10, 100 and 1,000 simulated/controlled active rooms separately before publishing capacity claims.

Use a short-lived in-memory audio pipeline with backpressure, fair guild scheduling, circuit breakers and strict cost budgets. Do not permanently queue general raw audio.

## Initial acceptance checklist

- [ ] DAVE voice **receive and decode** verified with real consented Discord calls, including key changes.
- [ ] Consent admit/withdraw/fail-closed tests, and guild configuration/authentication tests.
- [ ] Per-speaker mapping proven or classification abstains; no guessed penalties.
- [ ] Human-only severe sanctions; contextual test cases cover false positives, nonexplicit LGBTQ+ conversations, overlap, noise, languages and quoted speech.
- [ ] Restart, reconnect, missing permission, provider quota, backpressure and shutdown tested.
- [ ] Production-bound Discloud process, secrets and independent bot identity verified.
- [ ] Representative metrics, privacy review, rollback, regression suite and final diff completed.

## External references

- Discord [voice connections and DAVE](https://github.com/discord/discord-api-docs/blob/main/developers/topics/voice-connections.mdx)
- [DAVE protocol](https://github.com/discord/dave-protocol/blob/main/protocol.md)
- [Original implementation and scope: #517](https://github.com/UglyGameFace/Dank-Shield/issues/517)

## Secrets and deployment

Store **the Watch Yo Mouf bot token** only in its separate deployment environment (never in GitHub source, README, screenshots or issues). The same rule applies to Gemini API credentials and any future signed control-plane credentials. Do not enable voice monitoring merely because env variables exist.

The Discord Developer Portal app is installed in a test guild and the owner provided a live `/watchyo` response screenshot showing its gateway online. This verifies only command routing, not audio processing, provider access, or capacity.

## Gateway bootstrap (not yet voice moderation)

This repo includes an independent Python 3.11 Discord gateway app, configured through `discloud.config` with a **768 MB** allocation. It deliberately enables only Guild and Voice State gateway intents. No microphone connection, DAVE receive, audio buffers, transcription, AI review or staff enforcement runs in this release. The standalone `/watchyo` staff-only command reports this state honestly.

Set `WATCH_YO_MOUF_TOKEN` **only** in the new bot's Discloud environment. To register the global /watchyo command, enable `WATCH_YO_MOUF_SYNC_COMMANDS=true` for one successful start, then disable command sync. Use `python main.py` locally only with a separately provisioned token. No token or provider credentials are needed for offline tests. Do not use Dank Shield's Discord token.

Automatic sharding follows Discord's gateway recommendation. Advanced deployments may set both `WATCH_YO_MOUF_SHARD_COUNT` and `WATCH_YO_MOUF_SHARD_IDS` to partition gateways across workers; shard assignments must not overlap. This alone does **not** distribute voice processing or implement session ownership. An installed-server total does not imply that number of monitored voice connections.

Testing: `python -m unittest discover -s tests -v`, followed by `python -m compileall -q main.py watch_yo_mouf tests`. GitHub Actions executes those checks with Python 3.11 and 3.13. Live Discord, DAVE, Discloud deployment and high-concurrency capacity are not validated by those offline checks.

Source inspection in Dank Shield (main) identified the established `community_voice_caption_runtime.py` → `community_voice_receive.py` boundary, with a pinned DAVE-specific `discord-ext-voice-recv` source in its requirements. Companion extraction must validate live DAVE decode and keep Dank Shield's existing receiver authoritative until safe ownership cutover.


## DAVE and Opus dependency preflight (no listening)

The separate Watch Yo Mouf host now pins the same `discord.py[voice]==2.7.1` and reviewed `discord-ext-voice-recv` DAVE commit (`03dd1e2dafe85522cc458441cd5b143b136ac836`) used by Dank Shield's receive stack, plus `opuslib-next-bundled==0.1.1`. The staff-only `/watchyo` checks that `davey` imports, the receive extension exposes the inbound `PacketDecoder._dave_decrypt` hook, and native libopus can instantiate a real PCM decoder.

The result distinguishes **dependency/ABI preflight** from a **real live DAVE decode**. Even a passing preflight does not prove the companion decrypted audio, mapped a speaking member, complied with consent, or delivered an AI verdict. No voice connection, audio buffer, transcription, moderation, or automatic startup is added. A failing check leaves voice safety off and reports a non-secret dependency reason.

Next acceptance: verify the updated Discloud build starts under 768 MB; rerun `/watchyo` and confirm prerequisites, then work on a consented, single-room DAVE canary with explicit independent control-plane authority and reliable revocation. Do **not** enable monitoring or remove Dank Shield's authoritative receiver solely because this dependency preflight passes.


## Authenticated control-plane contract (proposed, not networked)

`watch_yo_mouf/voice_control.py` defines a **transport-neutral** version 1 HMAC-SHA256 event format for future Dank Shield → Watch Yo Mouf coordination. This is a security prerequisite, not a running integration. The project exposes no new HTTP route, Discord command, websocket, microphone receiver, or secret environment setting for this contract.

The authoritative Dank Shield voice-safety implementation is on its Discloud integration line (not the different public `main` tree). It owns settings in the existing guild configuration store, explicit `voice_safety_agreement_v1` member records in existing guild/member settings, admin UI, and the in-process `CommunityVoiceCaptionManager` DAVE receiver. Neither a Verified role nor Live Captions consent is a Voice Safety agreement. The public Bot API binds to `127.0.0.1`; do **not** expose it to the internet or assume another Discloud app can call it. No shared Supabase database capability or cross-host access has been established.

The signed JSON envelope has exactly `{"payload": {...}, "signature": "<sha256 hex>"}`, where `signature` is HMAC-SHA256 with an isolated secret of at least 32 random bytes over UTF-8 JSON of the payload using `sort_keys=True`, ASCII escaping, and compact `,:` separators. Sender and receiver must use the identical serializer. It admits only `policy`, `revoke`, and `stop` events, a unique 32-character lowercase hexadecimal nonce, positive Discord snowflake IDs, a strictly increasing per-guild sequence, and a lifetime no longer than 30 seconds. The signed `policy` fields are the desired `enabled` state and one monitored `channel_id`; `revoke` identifies one member ID; `stop` halts the room. Unknown fields, duplicate JSON keys, weak secrets, tampering, stale sequences, expiry and version mismatches are rejected. The in-memory gate handles revocation conservatively by halting the entire guild; later policy messages cannot clear the halt within the same process.

**Never interpret a valid `policy` envelope as authorization to listen.** The API explicitly admits zero audio. A safe later cutover additionally requires a mutually authenticated cross-host transport; a durable, centrally fenced single-receiver lease shared with the still-running Dank Shield process; fresh per-member positive consent checks and immediate revoke propagation; notice publication; revocation confirmation/fail-closed handling; DAVE per-speaker receive validation; and real Discloud CPU/RAM tests. Local memory and sequence checks are not a distributed lock. On restart or transport outage, monitoring must remain off. Do not put secrets, audio, or transcripts in signed control messages.

No extra `WATCH_YO_MOUF_*` environment variables are needed for this proposed offline contract. Provision a separate service-to-service key **only when** a real authenticated transport is implemented and reviewed; do not reuse the Discord token, Gemini API key, or Dank Shield's existing general Bot API secret.

Run `python -m unittest discover -s tests -v`; CI on Python 3.11 and 3.13 covers signed-envelope validation, tamper/replay/expiry protection, revocation precedence, and deny-by-default audio admission. This is not a live network or DAVE decryption acceptance test.

## Private Discloud VLAN handshake (two-repository staged rollout)

Dank Shield already has `VLAN=true` and `HOSTNAME=dankbot` on its site deployment. Discloud's private VLAN connects applications without adding a public route; the separate bot joins with `VLAN=true` and `HOSTNAME=watchyomouf`. The only new endpoint is a dedicated `GET http://dankbot:8097/v1/status` inside the VLAN, and it remains **off** until the host explicitly enables it. It does not alter the existing structured Bot API at `127.0.0.1:8081` or the site's public 8080 ingress.

The handshake uses a **separate shared random secret** (at least 32 bytes) and signed requests with a 30-second maximum clock skew and one-time nonce. Dank Shield rejects replay attempts and signs a fixed response stating it remains the policy/receiver authority and **voice_capture_authorized=false**. Watch Yo Mouf checks that signed reply on demand in staff-only `/watchyo`. It reports "authenticated (diagnostics only)" when successful, "disabled" by default, and "unavailable" for any auth/network/timeout/error failure. No member or guild records, sound, transcriptions, or credentials are transmitted.

**Deploy in this order after both narrow PRs pass:** (1) Merge/deploy the paired **Dank Shield** PR onto the exact Discloud integration branch (not a different `main` branch); (2) merge/deploy this **Watch Yo Mouf** PR, keeping RAM at 768 MB; (3) generate one strong random secret offline and configure it under `DANK_VOICE_BRIDGE_SECRET` and `WATCH_YO_MOUF_BRIDGE_SECRET` respectively without committing it; (4) enable `DANK_VOICE_BRIDGE_ENABLED=true` and `WATCH_YO_MOUF_BRIDGE_ENABLED=true`, restart both; (5) use `/watchyo` to verify the signed VLAN handshake. Turn either enabled flag back off to disable the diagnostic. Do not set an unverified random placeholder or reuse Discord/Gemini/API tokens.

This is a **network and authentication canary only**, not live policy synchronization, cross-process fencing, consent verification, Gemini processing, or the start of monitoring. After successful real Discloud tests, future work must add authoritative and durable lease ownership, per-member fresh consent checks, immediate opt-out, event ordering after restarts, and a controlled DAVE decode canary. VLAN visibility, DNS reachability, port policy, latency, deployment branch, RAM and process behavior have NOT yet been verified on your live Discloud containers.


## Troubleshooting the private bridge after enabling it

A Discord `/watchyo` response of `Private Dank Shield bridge: unavailable` from the original PR #4 reports only that the Watch Yo Mouf flag is enabled; it **cannot identify** the failure. The more precise private diagnostics in this PR distinguish: an invalid/missing Watch secret (before any network call); internal DNS lookup failure for `dankbot`; TCP connection refused on private port 8097; connection timeout or routing failure; HTTP 401 (wrong secrets or skewed host clocks); HTTP 503 (Dank Shield listener disabled); HTTP 404 (wrong deployed route/version); and a signed response format/authentication failure. No request headers, actual credentials, raw exception strings or audio are returned to Discord.

A positive `authenticated (diagnostics only)` result requires the paired deployed Dank Shield branch and the same independently generated 32+-byte bridge secret on both hosts. Watch Yo Mouf uses `VLAN=true, HOSTNAME=watchyomouf` and Dank Shield uses `VLAN=true, HOSTNAME=dankbot`; this code always connects exclusively to `http://dankbot:8097/v1/status` and ignores system HTTP proxies and redirects. Redeploy Watch Yo Mouf to see the new diagnostics, then run `/watchyo` from a staff account. Confirm the Discloud logs on Dank Shield show `Voice companion private status bridge listening on VLAN port 8097` and are not reporting a credential or binding error. The log doesn't prove live network reachability; use the signed response for that.

This update changes no monitoring permissions, guild policies, bot commands, environmental variable names, Discloud RAM allocation (768 MB), or live Voice Safety capture state. The receiver stays disabled. **Do not** expose port 8097 publicly or post either secret in Discord, issues, screenshots, or GitHub.


## Paired read-only member eligibility check (draft Voice Safety #517)

After live Discord `/watchyo` confirmed **authenticated (diagnostics only)**, this change introduces a separate signed, private `POST /v1/member-eligibility` contract on the existing 8097 VLAN listener. Dank Shield remains the sole owner of configured guild policy and versioned consent. The Watch Yo Mouf `read_member_eligibility(guild_id, member_id, channel_id)` method sends an on-demand body-bound HMAC query with a fresh nonce, never from startup or passive polling; only on an explicit staff self-check button. Replies contain only `consent_current` and `policy_matches`, and explicitly reject any attempt to authorize voice capture; failures return `None`.

No new environment variables, public route, bot permissions, new storage, voice connection, transcript, or AI processing is introduced. Existing `/v1/status` and current bot behavior are unchanged. Deploy **Dank Shield's paired PR first**, then this PR, and verify actual read-only private requests against a consenting test member and a withdrawn agreement. Positive eligibility is only a snapshot, **not permission to listen**. Durable fenced ownership, immediate revocation and live DAVE/MLS decoding remain mandatory before any monitoring or migration.


## Staff-only Discord consent canary (#517, pending deployment)

To exercise the previously merged **read-only** `/v1/member-eligibility` endpoint from Android without handling signatures or member IDs, a `Test My Consent` button is attached to the existing ephemeral staff-only `/watchyo` response. It requires **Manage Server** and is bound to the staff user who opened it. No additional slash command or command-sync setting is needed.

After updating Watch Yo Mouf from this PR, join the test server's **configured Voice Safety channel**, run `/watchyo`, then press `Test My Consent` within three minutes. A signed private request reads **only your own** current versioned Voice Safety agreement and whether that voice channel matches Dank Shield's saved monitored-room configuration. You can remain in the same VC and run it again after withdrawing your Voice Safety agreement to verify that consent changes from `recorded` to `not recorded`. This request happens only when you press the button. The bot never joins the VC, listens, records, transcribes, or sends member data into a public Discord message.

If the user isn't in a detectable VC, the button explains the prerequisite without issuing a network request. If the signed endpoint cannot be authenticated (wrong deployment, disabled VLAN listener, storage or network failure, incorrect response), it shows a generic fail-closed message, never a successful consent indication. `recorded` and `matches this VC` are diagnostic **snapshots**, not receiver permission. The response always states **Voice capture OFF**. No automatic monitoring or member consent assumptions are made. The channel must already be configured in Dank Shield; no need to enable actual voice capture or paid Gemini flags to run the read-only check.

This is a test surface only. Durable cross-process receiver lease/fencing, immediate revocation, provider gates, real DAVE per-speaker proof, host capacity and safe migration remain mandatory before anyone enables voice monitoring. Preserve the existing separate Dank Shield receiver unchanged.


## Voice #517: Live member eligibility failure, safer staged diagnostics

At 11:52 PM Android Discord, `/watchyo` returned **Private Dank Shield bridge: authenticated (diagnostics only)** but `Test My Consent` returned the generic **Member eligibility could not be authenticated**. These use distinct routes: GET `/v1/status` is a fast authenticated handshake; POST `/v1/member-eligibility` is a signed, read-only request that can also query Dank Shield guild configuration and current voice-specific agreement storage. A working GET does not establish POST health.

The merged source was inspected in both repos: shared `voice_member_wire.py` is byte-for-byte identical, POST path is registered on Dank Shield's existing VLAN-only port 8097, and Watch sends that route with a signed HMAC request. The live reason for POST failure is **not known** from the previous response; do not assume incorrect secrets, a missing server update, or unrecorded consent. The existing 1.5-second POST timeout was short for up to two fresh storage reads; the on-click probe now uses a bounded **6.0-second total/1.5-second connect** budget. The GET keeps its original timeout. A single staff-initiated request is made only on button click, not periodically.

`Test My Consent` now reports a **fixed sanitized stage** for a disabled Watch probe, invalid local request/key, timed-out POST, refused/unreachable VLAN, HTTP 401/404/409/413/500/503, oversized/invalid signed reply, or successful authenticated POST. No URL, secret, member ID, raw exception, response body, or audio is exposed in Discord. A valid negative agreement/policy returns a verified response and is **not** misreported as authentication failure. Any fault still denies eligibility and **never authorizes capture**.

Validation: exact-head Python 3.11/3.13 CI and diff review before merge. **Next:** deploy Watch Yo Mouf main only, join the configured Voice Safety VC, rerun `/watchyo → Test My Consent`, and use the new stage to fix the evidenced cause. No changes to Dank Shield, provider keys, environment switches or audio permissions are needed for this diagnostic.
