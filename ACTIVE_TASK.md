# Single active task: Watch Yo Mouf independent voice companion

**Outcome:** Establish and validate an independently hosted voice moderation companion for Dank Shield, preserving its stable core bot.
**Scope:** Initial independent service architecture, private signed control-plane contract, explicit per-member agreement and revocation, DAVE per-speaker receive, bounded AI processing, staff-only incidents, safe migration and capacity validation.
**Status:** Architecture bootstrapped in an empty new repository; implementation and real-world validation have **not** started. Do not label the bot functional.

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
4. Test a maintained DAVE receive dependency and its current documented versions before implementing a gateway.

## Changes
- `README.md`: product boundaries, privacy gates, architecture and acceptance checks.
- `.gitignore`: credential, evidence, audio and build artifact exclusions.
- This task-state record.

## Validation
- Repository existence and emptiness verified using connected GitHub read actions.
- No code implementation yet. No CI, build, end-to-end DAVE test, multi-speaker test, mobile acceptance or Discloud runtime acceptance.
- No access to Discord Developer Portal credentials via GitHub. Do not request posting secrets into chat.

## Cleanup and conflicts
- No pre-existing Watch Yo Mouf files to conflict with.
- Do not delete or change the current Dank Shield receiver until a verified migration canary and rollback path exist.

## Blockers and risks
- Need actual tested DAVE receive stack before asserting viability.
- Need explicit consent sync and privacy/legal/provider eligibility gates.
- Need isolated hosting, secrets, traffic quotas and measured worker capacity.
- The bot is **not deployed and not monitoring**.

## Backlog
- Rich multi-VC policy, additional model vendors, optional auto-enforcement and claimed competitor superiority only after the initial live receive/advisory flow and validation meet DoD.

## Next step
Inspect the current deployed Dank Shield branch and authoritative voice receiver/consent path, then create the smallest working DAVE receive canary in this repository on a focused branch with automated tests. Do not ship monitoring without proper consent and provider review.
