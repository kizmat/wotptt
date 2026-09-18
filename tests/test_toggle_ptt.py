import importlib.util
import logging
import sys
import types

logging.disable(logging.CRITICAL)


class Event(object):
    def __init__(self):
        self.handlers = []
    def __iadd__(self, fn):
        if fn not in self.handlers:
            self.handlers.append(fn)
        return self
    def __isub__(self, fn):
        if fn in self.handlers:
            self.handlers.remove(fn)
        return self
    def fire(self, *args):
        for fn in list(self.handlers):
            fn(*args)


class FakeVOIPManager(object):
    def __init__(self):
        self.onJoinedChannel = Event()
        self.muted = True
        self.history = []
        self.channel = 'platoon'
        self.testing = False
        self.initialized = True
        self.enabled = True
        self.channel_enabled = True
    def setMicMute(self, muted=True):
        self.muted = bool(muted)
        self.history.append(self.muted)
    def getCurrentChannel(self):
        return self.channel
    def isInTesting(self):
        return self.testing
    def isInitialized(self):
        return self.initialized
    def isEnabled(self):
        return self.enabled
    def isCurrentChannelEnabled(self):
        return self.channel_enabled


class FakeUnitMgr(object):
    def __init__(self):
        self.onUnitLeft = Event()


class FakePlatoonController(object):
    def __init__(self):
        self.in_platoon = False
        self.prbDispatcher = object()
        self.prbEntity = self
        self.active = True
    def isActive(self):
        return self.active
    def isInPlatoon(self):
        return self.in_platoon


class FakePlayer(object):
    pass


callbacks = []
keys_down = set()
player = FakePlayer()
voip = FakeVOIPManager()
unit_mgr = FakeUnitMgr()
platoon = FakePlatoonController()
current_ptt_key = [81]
roots = []


def callback(delay, fn):
    token = object()
    callbacks.append([token, delay, fn, False])
    return token


def cancel_callback(token):
    for item in callbacks:
        if item[0] is token:
            item[3] = True


def run_delay(delay):
    pending = [x for x in list(callbacks) if not x[3] and x[1] == delay]
    for item in pending:
        item[3] = True
        item[2]()


# BigWorld
m = types.ModuleType('BigWorld')
m.callback = callback
m.cancelCallback = cancel_callback
m.isKeyDown = lambda key: key in keys_down
m.player = lambda: player
sys.modules['BigWorld'] = m

# CommandMapping
m = types.ModuleType('CommandMapping')
class CmdMap(object):
    def get(self, name):
        assert name == 'CMD_VOICECHAT_MUTE'
        return current_ptt_key[0]
m.g_instance = CmdMap()
sys.modules['CommandMapping'] = m

# GUI
m = types.ModuleType('GUI')
class Text(object):
    def __init__(self, value=''):
        self.text = value
        self.visible = True
m.Text = Text
m.addRoot = lambda x: roots.append(x) if x not in roots else None
m.delRoot = lambda x: roots.remove(x) if x in roots else None
m.reSort = lambda: None
sys.modules['GUI'] = m

# VOIP
m = types.ModuleType('VOIP')
m.getVOIPManager = lambda: voip
sys.modules['VOIP'] = m

# PlayerEvents
pe = types.ModuleType('PlayerEvents')
class PlayerEventsState(object):
    def __init__(self):
        self.onAvatarBecomePlayer = Event()
        self.onAvatarBecomeNonPlayer = Event()
        self.onAccountShowGUI = Event()
        self.isPlayerEntityChanging = False
g_playerEvents = PlayerEventsState()
pe.g_playerEvents = g_playerEvents
sys.modules['PlayerEvents'] = pe

# helpers.dependency
helpers = types.ModuleType('helpers')
dep = types.ModuleType('helpers.dependency')
dep.instance = lambda iface: platoon
helpers.dependency = dep
sys.modules['helpers'] = helpers
sys.modules['helpers.dependency'] = dep

# gui.prb_control.prb_getters
gui_pkg = types.ModuleType('gui'); gui_pkg.__path__ = []
prb_pkg = types.ModuleType('gui.prb_control'); prb_pkg.__path__ = []
prb_getters = types.ModuleType('gui.prb_control.prb_getters')
prb_getters.getClientUnitMgr = lambda: unit_mgr
prb_pkg.prb_getters = prb_getters
sys.modules['gui'] = gui_pkg
sys.modules['gui.prb_control'] = prb_pkg
sys.modules['gui.prb_control.prb_getters'] = prb_getters

# skeletons.gui.game_control
sk = types.ModuleType('skeletons'); sk.__path__ = []
skg = types.ModuleType('skeletons.gui'); skg.__path__ = []
gc = types.ModuleType('skeletons.gui.game_control')
class IPlatoonController(object): pass
gc.IPlatoonController = IPlatoonController
sys.modules['skeletons'] = sk
sys.modules['skeletons.gui'] = skg
sys.modules['skeletons.gui.game_control'] = gc

# messenger.proto.bw_chat2.VOIPChatController
messenger = types.ModuleType('messenger'); messenger.__path__ = []
proto = types.ModuleType('messenger.proto'); proto.__path__ = []
bw = types.ModuleType('messenger.proto.bw_chat2'); bw.__path__ = []
vcmod = types.ModuleType('messenger.proto.bw_chat2.VOIPChatController')
class VOIPChatController(object):
    def invalidateMicrophoneMute(self):
        # Native EU 2.4.0.1: invalidation delegates to the existing mute hook.
        if current_ptt_key[0] not in keys_down:
            self.setMicrophoneMute(isMuted=True, force=True)
    def setMicrophoneMute(self, isMuted, force=False):
        if force or (voip.getCurrentChannel() and not voip.isInTesting()):
            voip.setMicMute(muted=isMuted)
vcmod.VOIPChatController = VOIPChatController
sys.modules['messenger'] = messenger
sys.modules['messenger.proto'] = proto
sys.modules['messenger.proto.bw_chat2'] = bw
sys.modules['messenger.proto.bw_chat2.VOIPChatController'] = vcmod

# Import mod
import os
MOD_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'mod_toggle_ptt.py'))
spec = importlib.util.spec_from_file_location('mod_toggle_ptt', MOD_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
original = VOIPChatController.setMicrophoneMute
mod.init()
ctrl = VOIPChatController()
manager = mod._manager
assert voip.history == [], 'startup must not change native mic state'


def press():
    keys_down.add(current_ptt_key[0])
    ctrl.setMicrophoneMute(False)


def release():
    keys_down.discard(current_ptt_key[0])
    ctrl.setMicrophoneMute(True)


# 1. Stock hold-to-talk outside platoon.
platoon.in_platoon = False
press(); assert voip.muted is False and not manager.latched
release(); assert voip.muted is True and not manager.latched

# 2. Joining a platoon alone must never open the microphone.
platoon.in_platoon = True
assert not manager.latched and voip.muted is True
# A stale positive controller result during loading cannot start a new latch.
platoon.active = False
press(); assert not manager.latched
release(); assert not manager.latched and voip.muted is True
platoon.active = True

# 2b. Toggle on in platoon; duplicate key-down must not double-toggle, and
# key-up must not mute the logical ON latch.
press(); assert manager.latched and voip.muted is False
ctrl.setMicrophoneMute(False)
assert manager.latched and voip.muted is False
release(); assert manager.latched and voip.muted is False
assert roots and roots[-1].text == 'PLATOON MIC: ON'
run_delay(3.0); assert not roots

# 3. Incidental native mute (e.g. text-chat focus) must not pause/mute.
ctrl.setMicrophoneMute(True)
assert manager.latched and voip.muted is False

# 4. Second press toggles off, cleans runtime state, and OFF hides after 3 seconds.
press(); assert not manager.latched and voip.muted is True
assert manager._unit_mgr is None
assert manager._battle_phase == mod._BATTLE_LOBBY
release(); assert not manager.latched and voip.muted is True
assert manager._watchdog_id is None
assert roots and roots[-1].text == 'PLATOON MIC: OFF'
run_delay(3.0); assert not roots

# 5. Configured PTT key is read live.
current_ptt_key[0] = 5
keys_down.clear()
press(); assert manager.latched and voip.muted is False
release(); assert manager.latched and voip.muted is False

# 5b. Missed key-up is recovered without changing the logical latch.
keys_down.add(current_ptt_key[0])
manager.key_down = True
keys_down.clear()
run_delay(1.0)
assert manager.latched and manager.key_down is False and voip.muted is False

# 6. Battle assembly transition must NOT clear the latch.
unit_mgr.onUnitLeft.fire(123, True)
assert manager.latched and voip.muted is False
assert manager._battle_phase == mod._BATTLE_PENDING

# 6b. Regression: at battle start the PlayerAvatar squad API can temporarily
# exist and report False before arena squad data is ready. Native WoT may also
# issue a mute during the transition. Neither may cancel an existing latch.
platoon.in_platoon = False
player.isPlayerInSquad = lambda: False
ctrl.setMicrophoneMute(True)
assert manager.latched and voip.muted is False
voip.muted = True
run_delay(1.0)
assert manager.latched and voip.muted is False

# Once battle squad membership is positively confirmed, the mod arms the
# in-battle leave detector.
player.isPlayerInSquad = lambda: True
run_delay(1.0)
assert manager.latched and voip.muted is False
assert manager._battle_phase == mod._BATTLE_CONFIRMED

# Battle end / return to lobby must preserve the ON latch even if the
# battle squad API goes False before the lobby exists again.
# Avatar destroys its arena, invalidates the mic, THEN emits non-player.
player.isPlayerInSquad = lambda: False
ctrl.invalidateMicrophoneMute()
assert manager.latched and voip.muted is False
g_playerEvents.isPlayerEntityChanging = True
g_playerEvents.onAvatarBecomeNonPlayer.fire()
player.isPlayerInSquad = lambda: False
voip.muted = True
run_delay(1.0)
assert manager.latched and voip.muted is False
assert manager._battle_phase == mod._BATTLE_PENDING

# Once the account/lobby is back, the same latch remains active.
del player.isPlayerInSquad
g_playerEvents.isPlayerEntityChanging = False
platoon.prbDispatcher = None
platoon.prbEntity = None
g_playerEvents.onAccountShowGUI.fire({})
voip.muted = True  # Physical capture can also be reset independently.
for _ in range(5):
    run_delay(1.0)
    assert manager.latched and voip.muted is False, 'early garage GUI must not clear latch'
# Dispatcher creation precedes initialization of its active entity.
platoon.prbDispatcher = object()
platoon.prbEntity = platoon
platoon.active = False
run_delay(1.0)
assert manager.latched and voip.muted is False
# A transient readiness lookup failure is also unknown, not a confirmed leave.
platoon.isActive = lambda: 1 / 0
run_delay(1.0)
assert manager.latched and voip.muted is False
del platoon.isActive
platoon.active = True
platoon.in_platoon = True
run_delay(1.0)
assert manager.latched and voip.muted is False
assert manager._battle_phase == mod._BATTLE_LOBBY

# 6c. Goal-audit regression: after a battle handoff, a missed unit-leave
# event must not leave the latch alive forever once the garage is authoritative.
manager._battle_phase = mod._BATTLE_PENDING
platoon.in_platoon = False
platoon.active = False
g_playerEvents.onAccountShowGUI.fire({})
run_delay(1.0)
assert manager.latched and voip.muted is False
platoon.active = True
run_delay(1.0)
assert not manager.latched and voip.muted is True
voip.onJoinedChannel.fire('channel', False, True)
run_delay(0.1)
assert not manager.latched and voip.muted is True
platoon.in_platoon = True
press(); release()
assert manager.latched and voip.muted is False

# 7. Real lobby unit leave/disband clears latch and mutes.
unit_mgr.onUnitLeft.fire(123, False)
assert not manager.latched and voip.muted is True

# 7b. Watchdog also catches a missed lobby leave event.
press(); release()
assert manager.latched and manager._battle_phase == mod._BATTLE_LOBBY
platoon.in_platoon = False
run_delay(1.0)
assert not manager.latched and voip.muted is True
platoon.in_platoon = True

# 8. Channel reconnect restores latched mic.
press(); release()
assert manager.latched and voip.muted is False
voip.muted = True
voip.onJoinedChannel.fire('channel', False, True)
run_delay(0.1)
assert manager.latched and voip.muted is False

# 8b. Confirmed in-battle squad membership followed by False is a real
# dynamic-platoon leave and must clear the latch.
platoon.in_platoon = False
player.isPlayerInSquad = lambda: True
run_delay(1.0)
assert manager._battle_phase == mod._BATTLE_CONFIRMED
player.isPlayerInSquad = lambda: False
run_delay(1.0)
assert not manager.latched and voip.muted is True
del player.isPlayerInSquad
platoon.in_platoon = True

# Re-open for the remaining self-heal tests.
press(); release()
assert manager.latched and voip.muted is False

# 9. Silent native/Vivox mic drop self-heals while the latch stays ON.
voip.muted = True
run_delay(1.0)
assert manager.latched and voip.muted is False

# 10. Intentional voice-channel disable must NOT be overridden.
voip.channel_enabled = False
voip.muted = True
run_delay(1.0)
assert manager.latched and voip.muted is True
voip.channel_enabled = True
run_delay(1.0)
assert manager.latched and voip.muted is False

# 10b. Global VOIP disable, no channel, and mic-test mode are respected.
voip.enabled = False
voip.muted = True
run_delay(1.0)
assert voip.muted is True
voip.enabled = True
voip.channel = ''
run_delay(1.0)
assert voip.muted is True
voip.channel = 'platoon'
voip.testing = True
run_delay(1.0)
assert voip.muted is True
voip.testing = False
run_delay(1.0)
assert voip.muted is False

# 11. Disabling setting clears an already-open latch.
platoon.in_platoon = True
assert manager.latched
mod._on_settings_changed(mod.MOD_ID, {'enabled': False, 'showIndicator': True})
assert not manager.latched and voip.muted is True

# 12. Indicator failure must never break microphone logic.
mod._on_settings_changed(mod.MOD_ID, {'enabled': True, 'showIndicator': True})
old_add_root = sys.modules['GUI'].addRoot
def failing_add_root(component):
    raise RuntimeError('simulated GUI failure')
sys.modules['GUI'].addRoot = failing_add_root
press(); assert manager.latched and voip.muted is False
release(); assert manager.latched and voip.muted is False
sys.modules['GUI'].addRoot = old_add_root
manager.hide_indicator()

# 13. fini restores the native hook and stale delayed callbacks cannot unmute.
voip.onJoinedChannel.fire('channel', False, True)
mod.fini()
voip.muted = True
run_delay(0.1)
assert voip.muted is True
assert VOIPChatController.setMicrophoneMute is original
assert not roots

# 14. Re-init after fini is clean and idempotent.
mod.init()
first_hook = VOIPChatController.setMicrophoneMute
mod.init()
assert VOIPChatController.setMicrophoneMute is first_hook
mod.fini()
assert VOIPChatController.setMicrophoneMute is original


# 15. Starting disabled must leave stock PTT behavior intact.
mod.SETTINGS['enabled'] = False
mod.init()
platoon.in_platoon = True
keys_down.clear()
press(); assert voip.muted is False and not mod._manager.latched
release(); assert voip.muted is True and not mod._manager.latched
mod.fini()
mod.SETTINGS['enabled'] = True

# 16. fini() must not overwrite a later mod that wraps our hook.
mod.init()
our_hook = VOIPChatController.setMicrophoneMute
def later_wrapper(self, isMuted, force=False):
    return our_hook(self, isMuted, force)
VOIPChatController.setMicrophoneMute = later_wrapper
mod.fini()
assert VOIPChatController.setMicrophoneMute is later_wrapper
voip.muted = True
platoon.in_platoon = False
keys_down.clear()
keys_down.add(current_ptt_key[0])
VOIPChatController().setMicrophoneMute(False)
assert voip.muted is False
VOIPChatController.setMicrophoneMute = original

print('ALL TESTS PASSED')
