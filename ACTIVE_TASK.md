# Single active task: Watch Yo Mouf independent voice companion

**Outcome:** Establish and validate an independently hosted voice moderation companion for Dank Shield, preserving its stable core bot.
**Scope:** Initial independent service architecture, private signed control-plane contract, explicit per-member agreement and revocation, DAVE per-speaker receive, bounded AI processing, staff-only incidents, safe migration and capacity validation.
**Status:** Standalone gateway bootstrap implemented on draft branch `feat/independent-gateway-bootstrap-20261012`; local configuration tests and syntax validation pass. GitHub CI, real dependency import, Discord login, DAVE receive, voice conduct classification and Discloud rollout are **not** yet validated. Do not label voice moderation functional.

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
- Six configuration tests passed locally; `compileall` passed locally. Local environment cannot install `discord.py` due blocked package network, so gateway-import smoke test is only queued for GitHub Actions. No exact-head CI, actual Discord login, end-to-end DAVE/multi-speaker test, mobile acceptance or Discloud runtime acceptance.
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

## Next step
Validate this draft gateway bootstrap CI and real Discord login on a consenting test guild; then trace the current Dank Shield voice consent/store and pinned `community_voice_receive.py` DAVE receive implementation before writing any Watch Yo Mouf audio canary. Keep receiver/consent/policy migration as the **same active task** and leave listening disabled until the privacy and DAVE gates pass.
