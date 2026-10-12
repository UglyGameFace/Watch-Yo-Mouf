# Single active task: Watch Yo Mouf independent voice companion

**Outcome:** Establish and validate an independently hosted voice moderation companion for Dank Shield, preserving its stable core bot.
**Scope:** Initial independent service architecture, private signed control-plane contract, explicit per-member agreement and revocation, DAVE per-speaker receive, bounded AI processing, staff-only incidents, safe migration and capacity validation.
**Status:** PR #1 gateway bootstrap merged; user set Discloud RAM to 768 MB and provided a live Discord `/watchyo` response (gateway online). Voice processing remains disabled. Next isolated slice is a read-only DAVE/Opus dependency preflight on `feat/dave-dependency-preflight-20261012`; live DAVE decode, consented voice admission, cross-bot control, AI triage and capacity remain unvalidated.

## Findings
- Repository `UglyGameFace/Watch-Yo-Mouf` was empty on 2026-10-12, before initialization.
- Source product specification: `UglyGameFace/Dank-Shield#517`. Draft and merged preliminary voice-safety PRs in Dank Shield do **not** establish a production-valid DAVE path.
- Prior Dank Shield UI reported Gemini key configured, but DAVE/voice-safety/paid-project/adult-eligibility host gates unmet and voice safety not running.
- Discord requires DAVE for voice. Python and JavaScript voice-receive libraries have had current DAVE receive regressions. Select a receiver only after verifying end-to-end **decoded** audio using a maintained library and real consented calls.
- The intended control plane is Dank Shield (policy/consent/staff UI). Watch Yo Mouf is the separately invited worker bot with its own token and hosting.

## Existing execution path to trace before code changes
1. In the **actual production branch** of Dank Shield: voice safety settings/verification consent storage → voice-state sessions → single `CommunityVoiceCaptionManager` → DAVE per-speaker reception → Gemini review → staff incident alerts.
2. Validate affected callers, selectors, persistence and opt-out sequence. Do not create duplicate receive paths or two authority sources.
3. Decide specific companion API and shared store based on available Discloud/network/runtime capabilities, protecting per-guild ownership and revocation.
4. Test actual DAVE receiver and documented versions before connecting a voice channel; initial gateway is slash-status only and has no audio path.

## Changes
- `README.md`: product boundaries, privacy gates, setup and acceptance checks.
- `.gitignore`/`.discloudignore`: exclude secrets, recordings and runtime data.
- `main.py`, `watch_yo_mouf/config.py`, `watch_yo_mouf/gateway.py`: isolated environment configuration, automatic/multiworker shard configuration, independent Discord gateway with slash status only.
- `requirements.txt`, `discloud.config` (originally 1024 MB, now owner-adjusted to **768 MB**, Python 3.11), `.env.example`: isolated deployment bootstrap.
- `tests/test_config.py`, `tests/test_gateway.py`, `.github/workflows/test.yml`: offline regression tests and Python 3.11/3.13 CI.

## Validation
- Repository existence and emptiness verified using connected GitHub read actions.
- Six configuration tests passed locally; `compileall` passed locally. Local package install was blocked by network restrictions. GitHub Actions installed pinned `discord.py==2.7.1`, compiled the project and passed all **9 unit tests** for Python 3.11 and Python 3.13 on implementation SHA `0adbe820af42f244d58aed8cf1dfcdb282ec5207`. Original CI failure was test cleanup calling `AutoShardedClient.close()` before login initialized its internal shard queue; corrected the test to not close a never-connected client and added direct admin authorization checks. Real Discord login, DAVE/multi-speaker tests, Android or Discloud acceptance and 10k-usage load remain unverified.
- No access to Discord Developer Portal credentials via GitHub. Do not request posting secrets into chat.

## Cleanup and conflicts
- No pre-existing Watch Yo Mouf files to conflict with. The gateway uses `discord.AutoShardedClient` rather than a second bot command/message handler; no audio listeners or alternative consent implementations have been introduced.
- Do not delete or change the current Dank Shield receiver until a verified migration canary and rollback path exist.

## Blockers and risks
- Need actual tested DAVE receive stack before asserting viability.
- Need explicit consent sync and privacy/legal/provider eligibility gates.
- Need isolated hosting, secrets, traffic quotas and measured worker capacity.
- The bot is **not deployed and not monitoring**.

## Backlog
- Rich multi-VC policy, additional model vendors, optional auto-enforcement and claimed competitor superiority only after the initial live receive/advisory flow and validation meet DoD.

## Pull request checkpoint
- Historical PR #1 **merged**: https://github.com/UglyGameFace/Watch-Yo-Mouf/pull/1; initial base `main` was `0b61a56b5511c87c8ee1f3975892861076ce8eb7`.
- Focused GitHub Actions run #38316601314: Python 3.11 and 3.13 jobs passed after fixing unconnected-client cleanup. Do not merge based solely on unit checks. Source remains gateway-only, audio entirely inactive.
- Discloud RAM allocation is now **768 MB**, as the owner confirmed and `discloud.config` records. This is not a tested figure for concurrent voice rooms or 10,000 installed guilds. Measure memory and CPU with real load.

## Next step
Validate this draft gateway bootstrap CI and real Discord login on a consenting test guild; then trace the current Dank Shield voice consent/store and pinned `community_voice_receive.py` DAVE receive implementation before writing any Watch Yo Mouf audio canary. Keep receiver/consent/policy migration as the **same active task** and leave listening disabled until the privacy and DAVE gates pass.

## 2026-10-12 continuation: DAVE dependency prerequisite slice

- **Scope:** Continue active Watch Yo Mouf / Dank Shield Voice Safety #517, no unrelated bot changes.
- **Current branch:** `feat/dave-dependency-preflight-20261012`, from merged Watch Yo Mouf `main` SHA `3c0957b244094b8c853a21bf682ce6248559cafe`. PR #1 merged and `discloud.config` is already `RAM=768` per owner.
- **Live checkpoint:** User-provided Discord screenshot of `/watchyo` confirms application installation, command registration, a responding bot gateway, and voice safety disabled. This is **not** proof of audio receive or STT.
- **Source trace:** Dank Shield's voice-safety integration branch `aaa-cinema-pre-pregateway-bind` at SHA `81b85ce16a3c84209e7cb7b3853d334604bafae6`: `voice_safety_consent.py` owns versioned member acceptance in existing member settings, `public_voice_safety.py` owns staff configuration/notice, `community_voice_caption_runtime.py` and `community_voice_receive.py` own the in-process DAVE receive lifecycle, `voice_safety_policy.py` owns advisory classification. Current standalone Watch Yo Mouf must **not** duplicate those authorities or start a competing capture listener.
- **Dependency finding:** Current Dank Shield receive pins discord.py[voice] 2.7.1, voice_recv commit `03dd1e2dafe85522cc458441cd5b143b136ac836` (inbound `_dave_decrypt`), and bundled libopus 0.1.1. The pinned upstream commit was inspected; static DAVE hook presence is not proof of real decoded traffic.
- **Changes:** Watch Yo Mouf requirements now pin the identical receive/Opus stack; `voice_readiness.py` performs import/hook/native decoder readiness only, with explicit failure reasons and no microphone connection. Staff-only `/watchyo` reports prerequisite status while continuing to say voice moderation is disabled. CI adds real import/native ABI and negative tests. README refreshed with deployment state and limits.
- **Validation:** PR #2 exact-head `e0624aa874acb14d96b76a39e29d2545d2f24c0d`, GitHub Actions run `38320148610` **passed** dependency installation, compilation, full unittest discovery, and secret-file checks on Python 3.11 and 3.13. Real dependency imports and bundled Opus decoder ABI were checked. No Discord DAVE call was performed in this change; updated Discloud 768 MB install/load and speaker tests require later canaries.
- **Cleanup/conflicts:** No existing companion receive implementation was replaced; current Dank Shield capture code remains untouched. No raw audio/transcripts introduced or persisted.
- **Blockers/risks:** Need exact-head CI and live dependency canary; then authenticated, versioned Dank Shield policy/consent transport, one-per-guild receiver lease/fencing, fail-closed withdrawal, and consented DAVE receive validation before enabling any audio.
- **Backlog:** Existing multi-VC policy, VoicePatrol performance benchmarking, automated sanctions, AntiNuke owner UX and branding requests remain outside this narrow slice.
- **Next step:** Finish PR #2 diff review and final exact-head CI on any checkpoint edits. After merging the narrow prerequisite, perform a 768 MB Discloud canary of updated `/watchyo`. Then implement and validate a single explicit-consent, isolated DAVE decode canary without switching task.


## 2026-10-12 post-PR #2 active handoff contract

- **Active task:** Watch Yo Mouf #517 independent voice moderation integration; no task switch.
- **Current branch:** `feat/signed-voice-control-contract-20261012`, based on Watch Yo Mouf `main` `6292b3e1634951c4303a4abbc003ee6b4abfcc70`. PR #2 merged. User's existing Discloud allocation is 768 MB. Initial gateway/live `/watchyo` verified previously; the **PR #2 decoder-ready message has not been reverified on the new deployment**.
- **Source-of-truth:** Dank Shield Discloud integration branch `aaa-cinema-pre-pregateway-bind` @ `81b85ce16a3c84209e7cb7b3853d334604bafae6` owns `public_voice_safety.py`, `voice_safety_consent.py`, `community_voice_caption_runtime.py` and `voice_safety_policy.py`. Separate public `main` may not reflect currently deployed Voice Safety. Voice Safety agreement `voice_safety_agreement_v1` is stored per guild/member and only affirmative disclosed records qualify. Cross-host structured Bot API is bound to `127.0.0.1` by default, so no accessible shared transport or distributed lease can be assumed.
- **Requirement/root issue:** The independent gateway lacks authoritative, authenticated cross-host voice policy and real-time opt-out/ownership updates; importing voice dependencies alone does not establish microphone admission or safe cutover.
- **Scope:** Versioned HMAC control-envelope contract with short expiry, per-guild monotonic sequences, nonce, exact schema, tamper/replay rejection, and conservative stop/revocation precedence. No HTTP/Discord transport, recording, AI keys, or competing voice receiver. `ControlGate.admits_audio` returns false unconditionally.
- **Changes:** `watch_yo_mouf/voice_control.py`, `tests/test_voice_control.py`, README and this task record only. No changes to Dank Shield production or its existing receiver.
- **Validation:** Check exact-head Python 3.11/3.13 CI, secrets scan, compilation, final diff. All live network, consent sync, DAVE decryption, joint-guild ownership lease, forced stop on lost service, revocation after restart, and 768 MB soak remain untested.
- **Cleanup/conflicts:** No extra API, persistent store or audio listener introduced. Existing shared API is localhost-only; never open publicly merely to connect the two bots.
- **Blockers/risks:** Need authenticated reachability between Discloud apps, correctly scoped shared secret, centrally enforced fencing/lease in an available durable store, authoritative revocation events and readbacks, and real shared-machine/multiworker failure tests before connecting voice. Signed messages **are not** a distributed lease or proof of consent.
- **Backlog:** Automatic punitive actions, 10k concurrent rooms, unrelated AntiNuke changes, other user-requested redesigns.
- **Next:** Validate this PR. Select a real transport and store after checking Discloud reachability and available quotas, then implement sender/receiver with authoritative consent/lease checks and controlled DAVE canary under the same #517 task.


## 2026-10-12 active continuation: private cross-Discloud bridge

- **Active/outcome:** Continue #517 Watch Yo Mouf voice moderation integration, without opening audio, altering existing Dank Shield receiver ownership, or switching tasks.
- **Source state:** Watch Yo Mouf PR #3 merged to main `ccc981189e73486fdd5eb7837316c0661b50ddec`; initial live `/watchyo` response verified by user, but updated PR #2/3 builds not rechecked on Discloud. Dank Shield target branch `aaa-cinema-pre-pregateway-bind` at `81b85ce16a3c84209e7cb7b3853d334604bafae6`. Separate public Dank Shield `main` differs, so PR must be based on the actual Discloud integration branch.
- **Root requirement:** Need authenticated host-to-host link before safe lease and per-member consent transport. Existing general Bot API binds `127.0.0.1:8081` and cannot be reached by Watch Yo Mouf without unsafe exposure. Discloud docs identify a private VLAN route; Dank Shield already has `VLAN=true, HOSTNAME=dankbot`.
- **Scope/changes:** Paired branches `Watch-Yo-Mouf:feat/voice-vlan-bridge-preflight-20261012` and `Dank-Shield:feat/517-private-companion-bridge-20261012`. Watch joins VLAN as `watchyomouf` while remaining `RAM=768`. Dedicated Dank Shield private `GET /v1/status` on port 8097, explicitly opt-in by env; one-time 30-second nonce and HMAC request/response, no public API or consent data. Watch's staff-only `/watchyo` checks this on demand with 1.5-second budget. Same source/interop fixture is vendored into both independent apps. Existing signed control contract is untouched.
- **Validation:** Pending exact-head GitHub Actions for both PRs. Cross-repo golden HMAC test; forged/tampered/stale request, response signature and non-recording assertions. Neither repo's deployment nor real VLAN connectivity has been verified. GitHub compilation/tests cannot establish reachability, no externally exposed port, or listener CPU overhead under Discloud.
- **Cleanup/conflicts:** No existing Discord voice receiver, guild config store, consent handler, general API authentication, Supabase, or website 8080 route altered. Narrow new opt-in listener bound to 8097 only. All enabling variables default to false.
- **Blockers/risks:** Need both PRs CI green, Discloud configuration of one new random shared key on both apps, VLAN routing, real Android /watchyo status, 768 MB memory checks. Cross-host consent propagation and centrally fenced receiver lease are **still absent**; audio remains off until proven.
- **Backlog:** Separate unrelated AntiNuke/branding feature requests not included. No punishment automation, 10k simultaneous VC claims, or broad redesign.
- **Next:** Validate both PR heads, review diffs, then staged merge (Dank Shield deployment branch first, Watch second), set matching private credentials and enable diagnostic only. Following live network acceptance, implement lease+consent transport within same active #517 task and run real opt-in DAVE decode.
