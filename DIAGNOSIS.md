# Battle-to-garage diagnosis: 1.4.3

## Evidence

Baseline: downloaded `TogglePlatoonPTT_v1.4.2_FULL_BUILD.zip`, SHA-256
`eab58038ae76e16a3d414477d0db08a5ece56fae3d036e2387bcc8488f563fea`.
This is the earlier v1.4.2 archive, not the later lessons archive. It contained
a stale v1.4.1 README and CHANGELOG despite the conversation's cleanup claim.

Installed game and reference both report EU `v.2.4.0.1 #952`, client 2619847,
overrides 2620046. Reference repository commit:
`0ff1890d1a24d43cf186b86a295bbc7dec63de56` in `izeberg/wot-src`.
This is a community decompile of the client, not a Wargaming-supported API.

The local game log confirms v1.4.2 started at 14:11:19 on 2026-09-18.
At 14:14:47 avatar teardown starts; account showGUI occurs at 14:14:48.592;
hangar initialization completes around 14:14:52.254 and the squad view appears
at 14:14:52.462. The log does not record the mod's latch or every mic call, so
it supports the initialization timing but does not prove the exact live mute cause.

## Native call trace

- [Avatar.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/Avatar.py):
  `onBecomeNonPlayer` stops the GUI/session provider, destroys the arena,
  calls `invalidateMicrophoneMute`, then emits `onAvatarBecomeNonPlayer`.
- [VOIPChatController.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/messenger/proto/bw_chat2/VOIPChatController.py):
  invalidation checks the configured PTT key and calls `setMicrophoneMute(True,
  force=True)` when released. This goes through the existing mod hook.
- [VOIPManager.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/VOIP/VOIPManager.py):
  `setMicMute` reaches BigWorld VOIP enable/disableMicrophone. This controls game
  capture, not the Windows device mute setting.
- [Account.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/Account.py)
  emits `onAccountShowGUI` before asynchronous garage setup completes.
- [personality.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/gui/shared/personality.py)
  later creates the prebattle dispatcher in `__initializeHangar`.
- [dispatcher.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/gui/prb_control/dispatcher.py)
  starts with an inactive entity; normal entity initialization activates it.
- [platoon_controller.py](https://github.com/izeberg/wot-src/blob/0ff1890d1a24d43cf186b86a295bbc7dec63de56/sources/res/scripts/client/gui/game_control/platoon_controller.py)
  returns False from `isInPlatoon` when no dispatcher/entity exists.

## Reproduced defect and minimal fix

v1.4.2 sets the phase to lobby on account GUI notification. The watchdog then
treats the temporary False as a real leave, clears the latch, and mutes capture.
Later readiness/channel joins cannot recover a latch that was cleared.

The new regression invokes native invalidation before the non-player event,
then emits account GUI while the dispatcher is absent, advances five watchdog
ticks, creates an inactive entity, and finally activates the platoon. It also
simulates a separate physical capture reset. Against unchanged v1.4.2 source it
fails with `early garage GUI must not clear latch`; with 1.4.3 it passes.

Only the lobby membership query and its watchdog consumer change: return None
for missing/inactive state or exceptions, and clear on explicit False only.
No new hook, timer, persistent state, or arbitrary grace period is added.
Existing explicit leave handling remains immediate. An active non-platoon
entity clears the latch on the next tick, including after a missed leave event.

## Validation boundary

The full mock suite and Python 2.7.18 compilation pass. The native call path
alone already preserves the latch on v1.4.2; an extra invalidation hook is not
justified. The readiness failure is reproduced locally and consistent with
the live log. The developer did not perform a live audio test. On 2026-09-18,
the user tested v1.4.3 and reported "this fixed it", confirming resolution of
the reported garage-return failure in their scenario. Other modes and the full
live checklist are not implied to have been verified by that report.
