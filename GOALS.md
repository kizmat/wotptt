# Toggle Platoon PTT - Goals

This file is the behavioral contract for the mod. Code changes should be checked against these goals before release.

## 1. Convert WoT platoon PTT into a toggle

- Use the Push-to-Talk key configured in World of Tanks.
- Do not introduce a second custom hotkey.
- First physical PTT press while in a supported platoon voice context turns the microphone ON.
- Releasing the key does not mute an ON latch.
- Second physical PTT press turns the microphone OFF.
- Joining a platoon must never turn the microphone on automatically.

## 2. Preserve the latch for the whole platoon session

An ON latch should remain ON across normal client transitions while the player remains in the same platoon:

- garage -> battle loading;
- battle loading -> active battle;
- active battle -> garage;
- temporary VOIP channel loss/rejoin;
- temporary lobby/battle state gaps while WoT replaces the player entity.

The user should not need to cycle the PTT key simply because a battle starts or ends.

## 3. Turn OFF when the platoon relationship really ends

- Leaving, being kicked from, or disbanding the lobby platoon must force the latch OFF as soon as WoT provides an authoritative leave signal.
- A confirmed in-battle squad leave must force the latch OFF.
- If an event is missed, the watchdog must provide a fallback check.
- Temporary loading/teardown states must not be mistaken for a real leave.

## 4. Preserve native WoT behavior outside the feature scope

- When the feature is disabled, WoT hold-to-talk behavior must remain unchanged.
- When the player is not in a supported platoon voice context and no latch is active, WoT hold-to-talk behavior must remain unchanged.
- The mod must not replace WoT's voice system; it should intercept only the minimum path required for the toggle.
- The separate WoT voice-channel enable/disable control must remain authoritative.
- Microphone-test mode must not be unmuted by the self-heal logic.

## 5. Keep logical and physical microphone state synchronized

- The logical ON latch is authoritative while the supported platoon session remains valid.
- If WoT/Vivox silently disables microphone capture while the latch remains ON, the mod should reopen it automatically.
- Self-healing must only run when VOIP is initialized and enabled, a current channel exists, that channel is enabled, and WoT is not in microphone-test mode.
- Reasserting an ON latch must not enable a voice channel the user deliberately disabled.

## 6. Input handling must be robust

- Read `CMD_VOICECHAT_MUTE` live rather than hardcoding a key such as Q.
- Binding changes should take effect without restarting the client.
- Duplicate/autorepeat key-down events must not double-toggle.
- A missed key-up must clear only the physical key debounce state; it must not clear the logical microphone latch.

## 7. Status feedback must be simple and transient

- Manual ON shows `PLATOON MIC: ON`.
- Manual OFF shows `PLATOON MIC: OFF`.
- Forced OFF may also show `PLATOON MIC: OFF` when appropriate.
- Both status messages remain visible for approximately 3 seconds, then disappear.
- Hiding the status message must never change the microphone latch.
- Indicator/UI failures must never break microphone behavior.

## 8. Session state must not persist across a client restart

- Feature settings may persist through the optional settings API.
- The microphone ON/OFF latch must never persist across a World of Tanks restart.
- Starting the mod must not change the microphone state until the user activates the feature.

## 9. Lifecycle and compatibility goals

- `init()` and `fini()` must be safe and idempotent.
- Event subscriptions and callbacks must be removed when no longer needed.
- Manual OFF should clean stale runtime subscriptions/state immediately.
- Unloading the mod must not leave delayed callbacks capable of reopening the mic.
- Hook teardown must not overwrite a later wrapper installed by another mod.
- Optional settings or HUD integrations must not be required for the core feature.

## 10. Scope

The primary supported target is the standard World of Tanks platoon voice path that uses `VOIPChatController.setMicrophoneMute`.

Some special game modes use their own VOIP controllers and bypass that standard path. They are not considered supported merely because standard platoon voice works. Mode-specific hooks should only be added when live testing demonstrates a real requirement; avoiding unnecessary special-mode patches is a deliberate maintainability goal.

## Release acceptance

Before a release is considered ready for live testing, the mock regression suite should cover at least:

- stock PTT outside a platoon;
- toggle ON, release, toggle OFF;
- duplicate/missed key events;
- live PTT-key rebinding;
- battle start persistence;
- battle end persistence;
- real lobby leave/disband;
- confirmed in-battle leave;
- missed leave-event fallback;
- VOIP reconnect;
- silent microphone failure/self-heal;
- disabled global VOIP;
- disabled current channel;
- no current channel;
- microphone-test mode;
- optional HUD failure;
- feature disable;
- clean unload/reload;
- coexistence with a later monkey-patch wrapper.

## Garage readiness acceptance (1.4.3)

- Account GUI notification alone must not establish a confirmed platoon absence.
- Missing dispatcher/entity, inactive entity, and query errors are unknown state.
- Preserve an existing latch across this gap without a fixed timeout.
- Once the prebattle entity is active, a confirmed no-platoon result must mute
  on the next watchdog tick even when the explicit leave event was missed.
- Exercise native invalidation before the avatar non-player event; check both
  logical latch and physical microphone state through delayed garage startup.
