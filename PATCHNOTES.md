# Toggle Platoon PTT - Patch Notes

## 1.4.3

- Fixed a reproduced battle-to-garage race: `onAccountShowGUI` runs before
  prebattle dispatcher/entity initialization. Treat missing/inactive state as
  unknown; only an active prebattle entity can confirm no platoon.
- Keep the existing mute hook: native `invalidateMicrophoneMute()` already
  delegates through it. No additional microphone hooks or polling added.
- Added regression coverage for native teardown invalidation, delayed garage
  initialization, inactive entities, readiness lookup errors, physical mic
  recovery, and confirmed no-platoon return after a missed leave event.
- Updated source and package metadata to 1.4.3; included Python 2.7 build.
- Imported the v1.4.2 full developer baseline into the repository (which
  previously held v1.3.0). Corrected stale README/history packaging and added
  reconstructed engineering lessons; the later 65-lesson archive was unavailable.
- Corrects the v1.4.2 claim below: account GUI visibility is not authoritative
  evidence that the garage platoon controller has finished initialization.
- Regression tests and compilation pass; live audio verification remains pending.

## 1.4.2

- Moved the behavioral contract into `GOALS.md`.
- Moved version history into `PATCHNOTES.md`.
- Reduced `README.md` to install/build/test/usage documentation.
- Added an authoritative garage-ready checkpoint using `onAccountShowGUI`.
- This closes an audit edge case where a battle-exit `PENDING` state could survive indefinitely if the lobby unit-leave event was missed and the player was no longer in a platoon.
- Renamed the shared status timeout constant to `STATUS_DISPLAY_SECONDS` because it controls both ON and OFF messages.
- Re-audited source behavior against every goal in `GOALS.md` and expanded regression coverage for the new lobby-authority fallback.
- Hardened shutdown cleanup so player-event unsubscriptions are attempted independently.

## 1.4.1

- Fixed battle -> garage regression where the latch could be cleared during avatar teardown.
- Added explicit avatar lifecycle handling for battle entry and exit.
- Added `isPlayerEntityChanging` guard around confirmed in-battle leave detection.
- Restored 3-second fade behavior for both ON and OFF status messages.

## 1.4.0

- Full runtime-state refactor and audit.
- Replaced separate battle transition flags with one explicit three-state phase.
- Added missed lobby-leave fallback detection.
- Manual OFF now immediately unbinds unit events and cleans state.
- Added regression coverage for lost key-up, VOIP/test/channel gating, battle start, battle end, missed lobby leave, hook coexistence, and cleanup.
- Audited against EU client source 2.4.0.5450.

## 1.3.2

- Fixed the observed battle-start bug where a latched platoon microphone could switch OFF as the match loaded.
- An existing ON latch became authoritative across lobby/battle transitions.
- Early `isPlayerInSquad() == False` results during battle initialization are ignored until battle squad membership has first been confirmed True.
- A later confirmed True -> False transition detects a real in-battle dynamic-platoon leave and forces the microphone OFF.
- Native WoT mute requests during battle loading no longer cancel an existing latch.
- Battle-end return to the lobby preserves the ON latch.

## 1.3.1

- Added self-healing for the observed condition where the mod remained logically ON but Vivox/BigWorld stopped transmitting.
- While latched ON, the watchdog reasserts microphone-open state once per second.
- Reassertion is gated by VOIP initialization, global VOIP enable state, current channel availability, current-channel enable state, and microphone-test mode.
- Deliberately disabling the WoT voice channel is respected.
- Added regression tests for silent microphone drop and intentional channel disable.

## 1.3.0

- Simplified lifecycle and state handling.
- Removed PAUSED/text-chat behavior.
- Removed Last Stand-specific hooks.
- Reduced continuous state synchronization.
- Added safer hook teardown and transition handling.

## 1.2.1

- Refactored the original implementation.
- Added platoon leave/disband handling, VOIP reconnect restoration, HUD indicator, settings integration, and mock-runtime tests.
