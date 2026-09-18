# Lessons learned

These lessons are reconstructed from the available conversation, v1.4.2 source,
and this investigation. The later archive containing the original 65 lessons
was not available; this file does not claim to reproduce its missing contents.

## State and lifecycle

1. Separate the logical latch from physical microphone capture and HUD visibility.
2. Treat membership as true, false, or unknown. An unavailable API is not a leave.
3. `onAccountShowGUI` starts garage setup; it does not finish prebattle setup.
4. Require a dispatcher and active prebattle entity before trusting lobby absence.
5. Dispatcher creation alone is insufficient: its initial entity is inactive.
6. Do not solve asynchronous readiness with an arbitrary time delay.
7. Keep a fallback for a missed leave event after readiness is established.
8. An early false battle squad result is normal until membership is confirmed.
9. A confirmed battle true-to-false change still means a real leave unless the
   entity is changing; do not disable this safeguard to preserve transitions.
10. An explicit unit leave/disband must still force OFF immediately.
11. Never persist an ON latch across client restart.

## Native voice and input

12. Trace callees before adding hooks. Invalidation already calls the mute hook.
13. Avatar teardown invalidates the mic before the non-player notification.
14. Direct VOIP-manager calls can change capture independently of the latch.
15. Self-heal must respect initialization, voice/channel disable, absent channel,
    and microphone-test mode.
16. Read the current PTT mapping, never assume Q or another fixed key.
17. Debounce duplicate key-down and recover missed key-up independently of latch.
18. Joining a platoon must never open the mic automatically.
19. Keep native hold-to-talk outside the supported platoon context.
20. Do not claim special-mode support from standard-path tests.

## Cleanup, tests, and releases

21. Cancel unnecessary watchdog callbacks and remove unit subscriptions on OFF.
22. Delayed callbacks must check running/latch state before reopening capture.
23. Unsubscribe handlers independently so one failure cannot prevent cleanup.
24. Restore a hook only if it is still yours; preserve wrappers from other mods.
25. Optional HUD/settings errors must not break voice behavior.
26. ON and OFF messages disappear after three seconds without altering capture.
27. Mock native call order and initialization gaps, not just the desired end state.
28. Prove a regression fails on the old code and passes after the minimal fix.
29. Check both the latch and physical mic, and preserve real-leave negative tests.
30. Record the client source commit and compare its version with the installed game.
31. Logs establish timing and loaded version, not proof of successful audio delivery.
32. Mock success and bytecode compilation are not live-client verification.
33. Match source and metadata versions; compile production bytecode with Python 2.7.
34. Check archive contents and bytecode magic; exclude caches, local paths and logs.
35. Maintain README instructions, GOALS requirements, and PATCHNOTES history separately.
36. Verify actual archive contents; prior completion messages are not sufficient.
37. Keep only one installed mod version, including standalone res_mods copies.

## Release checklist

- Run stock PTT, toggle, repeat key, key rebinding and missed key-up tests.
- Run battle entry and native teardown -> delayed garage -> active platoon tests.
- Test real leave, missed leave, reconnect and intentional voice disable.
- Verify HUD timeout, disabled settings, cleanup, reload and hook coexistence.
- Compile with Python 2.7.18; inspect package metadata and archive contents.
- Verify the developer ZIP includes source, tests, build helpers and documentation.
- Confirm audio with a platoon member through entry/exit in the live client.
