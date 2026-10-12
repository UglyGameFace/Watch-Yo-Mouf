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
- `requirements.txt`, `discloud.config` (1024 MB Python 3.11), `.env.example`: isolated deployment bootstrap.
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
- Draft PR: https://github.com/UglyGameFace/Watch-Yo-Mouf/pull/1; base `main` at `0b61a56b5511c87c8ee1f3975892861076ce8eb7`.
- Focused GitHub Actions run #38316601314: Python 3.11 and 3.13 jobs passed after fixing unconnected-client cleanup. Do not merge based solely on unit checks. Source remains gateway-only, audio entirely inactive.
- RAM allocation `1024 MB` is an initial canary budget, **not** a tested figure for 10,000 guilds or concurrent rooms. Use separate workers, measured caches and budgets before scaling.

## Next step
Validate this draft gateway bootstrap CI and real Discord login on a consenting test guild; then trace the current Dank Shield voice consent/store and pinned `community_voice_receive.py` DAVE receive implementation before writing any Watch Yo Mouf audio canary. Keep receiver/consent/policy migration as the **same active task** and leave listening disabled until the privacy and DAVE gates pass.

## 2026-10-12 continuation: DAVE dependency prerequisite slice

- **Scope:** Continue active Watch Yo Mouf / Dank Shield Voice Safety #517, no unrelated bot changes.
- **Current branch:** `feat/dave-dependency-preflight-20261012`, from merged Watch Yo Mouf `main` SHA `3c0957b244094b8c853a21bf682ce6248559cafe`. PR #1 merged and `discloud.config` is already `RAM=768` per owner.
- **Live checkpoint:** User-provided Discord screenshot of `/watchyo` confirms application installation, command registration, a responding bot gateway, and voice safety disabled. This is **not** proof of audio receive or STT.
- **Source trace:** Dank Shield's voice-safety integration branch `aaa-cinema-pre-pregateway-bind` at SHA `81b85ce16a3c84209e7cb7b3853d334604bafae6`: `voice_safety_consent.py` owns versioned member acceptance in existing member settings, `public_voice_safety.py` owns staff configuration/notice, `community_voice_caption_runtime.py` and `community_voice_receive.py` own the in-process DAVE receive lifecycle, `voice_safety_policy.py` owns advisory classification. Current standalone Watch Yo Mouf must **not** duplicate those authorities or start a competing capture listener.
- **Dependency finding:** Current Dank Shield receive pins discord.py[voice] 2.7.1, voice_recv commit `03dd1e2dafe85522cc458441cd5b143b136ac836` (inbound `_dave_decrypt`), and bundled libopus 0.1.1. The pinned upstream commit was inspected; static DAVE hook presence is not proof of real decoded traffic.
- **Changes:** Watch Yo Mouf requirements now pin the identical receive/Opus stack; `voice_readiness.py` performs import/hook/native decoder readiness only, with explicit failure reasons and no microphone connection. Staff-only `/watchyo` reports prerequisite status while continuing to say voice moderation is disabled. CI adds real import/native ABI and negative tests. README refreshed with deployment state and limits.
- **Validation:** Pending exact-head GitHub Actions (Python 3.11 and 3.13) and diff review. No local networked install or Discord DAVE call was performed in this change; Discloud 768 MB dependency install/load and speaker tests require later canaries.
- **Cleanup/conflicts:** No existing companion receive implementation was replaced; current Dank Shield capture code remains untouched. No raw audio/transcripts introduced or persisted.
- **Blockers/risks:** Need exact-head CI and live dependency canary; then authenticated, versioned Dank Shield policy/consent transport, one-per-guild receiver lease/fencing, fail-closed withdrawal, and consented DAVE receive validation before enabling any audio.
- **Backlog:** Existing multi-VC policy, VoicePatrol performance benchmarking, automated sanctions, AntiNuke owner UX and branding requests remain outside this narrow slice.
- **Next step:** Review exact-head CI and fix any failures on this branch. After merging the narrow prerequisite, perform 768 MB Discloud canary of updated `/watchyo`. Then implement and validate a single explicit-consent, isolated DAVE decode canary without switching task.
