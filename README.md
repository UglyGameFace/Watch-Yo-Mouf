# Watch Yo Mouf

Dedicated Discord voice-safety companion for [Dank Shield](https://github.com/UglyGameFace/Dank-Shield).

**Status: repository initialized; no audio capture, transcription, or moderation is implemented or deployed here yet.** A configured Discord Developer Portal application alone does not start a bot.

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

The Discord Developer Portal app and repository are already created. Hosting is **not yet verified**; no invite, deployed process, running gateway or functioning AI pipeline is claimed.
