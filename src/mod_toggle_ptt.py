# -*- coding: utf-8 -*-
"""Toggle Push-to-Talk for World of Tanks platoon voice chat."""
from __future__ import absolute_import

import logging

import BigWorld
import CommandMapping
import GUI
import VOIP

from gui.prb_control import prb_getters
from PlayerEvents import g_playerEvents
from helpers import dependency
from messenger.proto.bw_chat2.VOIPChatController import VOIPChatController
from skeletons.gui.game_control import IPlatoonController


MOD_ID = 'panda_toggle_platoon_ptt'
MOD_NAME = 'Toggle Platoon PTT'
MOD_VERSION = '1.4.3'
SETTINGS_VERSION = 1

WATCHDOG_SECONDS = 1.0
STATUS_DISPLAY_SECONDS = 3.0

_BATTLE_LOBBY = 0
_BATTLE_PENDING = 1
_BATTLE_CONFIRMED = 2

SETTINGS = {'enabled': True, 'showIndicator': True}

_logger = logging.getLogger(MOD_ID)
_manager = None
_original_set_mute = None
_patched_set_mute = None


def _apply_settings(values):
    if not isinstance(values, dict):
        return
    for key in ('enabled', 'showIndicator'):
        if key in values:
            SETTINGS[key] = bool(values[key])


def _on_settings_changed(linkage, values):
    if linkage != MOD_ID:
        return

    was_enabled = SETTINGS['enabled']
    _apply_settings(values)

    if _manager is None:
        return
    if was_enabled and not SETTINGS['enabled']:
        _manager.force_off(show_status=True)
    _manager.refresh_indicator()


def _register_settings():
    try:
        from gui.aslainMenu import g_modsSettingsApi as api, templates
    except ImportError:
        try:
            from gui.modsSettingsApi import g_modsSettingsApi as api, templates
        except ImportError:
            return

    try:
        template = {
            'modDisplayName': '%s v%s' % (MOD_NAME, MOD_VERSION),
            'settingsVersion': SETTINGS_VERSION,
            'enabled': SETTINGS['enabled'],
            'column1': [
                templates.createCheckbox(
                    'Show microphone status',
                    'showIndicator',
                    SETTINGS['showIndicator'],
                    tooltip=(
                        '{HEADER}Microphone status{/HEADER}'
                        '{BODY}ON and OFF disappear after 3 seconds.{/BODY}'
                    )
                )
            ],
            'column2': []
        }
        saved = api.setModTemplate(MOD_ID, template, _on_settings_changed)
        if saved:
            _apply_settings(saved)
    except Exception:
        _logger.exception('Settings panel registration failed.')


class TogglePTT(object):

    def __init__(self):
        self.running = False
        self.latched = False
        self.key_down = False
        self._battle_phase = _BATTLE_LOBBY
        self._watchdog_id = None
        self._unit_mgr = None
        self._indicator = None
        self._indicator_added = False
        self._indicator_token = 0

    def start(self):
        if self.running:
            return
        self.running = True
        VOIP.getVOIPManager().onJoinedChannel += self._on_joined_channel
        g_playerEvents.onAvatarBecomePlayer += self._on_avatar_become_player
        g_playerEvents.onAvatarBecomeNonPlayer += self._on_avatar_become_non_player
        g_playerEvents.onAccountShowGUI += self._on_account_show_gui

    def stop(self):
        if not self.running:
            return

        self.running = False
        self._cancel_watchdog()
        if self.latched:
            self._set_mic(True)
        self._clear_latch_state()
        self.hide_indicator()

        try:
            VOIP.getVOIPManager().onJoinedChannel -= self._on_joined_channel
        except Exception:
            pass
        player_events = (
            (g_playerEvents.onAvatarBecomePlayer, self._on_avatar_become_player),
            (g_playerEvents.onAvatarBecomeNonPlayer, self._on_avatar_become_non_player),
            (g_playerEvents.onAccountShowGUI, self._on_account_show_gui),
        )
        for event, handler in player_events:
            try:
                event -= handler
            except Exception:
                pass

    @staticmethod
    def _battle_squad_state():
        """True/False in battle; None when there is no active battle avatar."""
        try:
            checker = getattr(BigWorld.player(), 'isPlayerInSquad', None)
            if callable(checker):
                return bool(checker())
        except Exception:
            pass
        return None

    @staticmethod
    def _lobby_platoon_state():
        """True/False only with an active prebattle entity; None during loading."""
        try:
            controller = dependency.instance(IPlatoonController)
            if (controller is None or controller.prbDispatcher is None
                    or controller.prbEntity is None
                    or not controller.prbEntity.isActive()):
                return None
            return bool(controller.isInPlatoon())
        except Exception:
            return None

    @classmethod
    def _can_toggle_here(cls):
        if cls._battle_squad_state() is True:
            return True
        return cls._lobby_platoon_state()

    @staticmethod
    def _ptt_down():
        try:
            key = CommandMapping.g_instance.get('CMD_VOICECHAT_MUTE')
            return bool(BigWorld.isKeyDown(key))
        except Exception:
            return False

    def _bind_unit_mgr(self):
        try:
            manager = prb_getters.getClientUnitMgr()
        except Exception:
            manager = None

        if manager is self._unit_mgr:
            return
        self._unbind_unit_mgr()
        if manager is None:
            return

        try:
            manager.onUnitLeft += self._on_unit_left
            self._unit_mgr = manager
        except Exception:
            self._unit_mgr = None

    def _unbind_unit_mgr(self):
        manager = self._unit_mgr
        self._unit_mgr = None
        if manager is None:
            return
        try:
            manager.onUnitLeft -= self._on_unit_left
        except Exception:
            pass

    def _on_unit_left(self, _, is_finished_assembling):
        if is_finished_assembling:
            # Lobby -> battle handoff. Arena squad data may report False until
            # the battle data provider has finished populating.
            self._battle_phase = _BATTLE_PENDING
        elif self.latched:
            self.force_off(show_status=True)

    def _on_avatar_become_player(self):
        if self.latched:
            self._battle_phase = _BATTLE_PENDING
            self._ensure_watchdog()

    def _on_avatar_become_non_player(self):
        if self.latched:
            # Battle -> lobby handoff. Squad data can disappear before the
            # lobby platoon controller is available again. Preserve the latch.
            self._battle_phase = _BATTLE_PENDING
            self._ensure_watchdog()

    def _on_account_show_gui(self, *args, **kwargs):
        if self.latched:
            # Account.showGUI precedes prebattle dispatcher/entity setup.
            # Switch phase now, but only an active entity may confirm a leave.
            self._battle_phase = _BATTLE_LOBBY
            self._bind_unit_mgr()
            self._ensure_watchdog()

    def _on_joined_channel(self, *args, **kwargs):
        if not self.latched:
            return
        try:
            BigWorld.callback(0.1, self._keep_mic_open)
        except Exception:
            self._keep_mic_open()

    def _ensure_watchdog(self):
        if (not self.running or self._watchdog_id is not None
                or not (self.latched or self.key_down)):
            return
        try:
            self._watchdog_id = BigWorld.callback(WATCHDOG_SECONDS, self._watchdog)
        except Exception:
            self._watchdog_id = None

    def _cancel_watchdog(self):
        callback_id = self._watchdog_id
        self._watchdog_id = None
        if callback_id is None:
            return
        try:
            BigWorld.cancelCallback(callback_id)
        except Exception:
            pass

    def _watchdog(self):
        self._watchdog_id = None
        if not self.running:
            return

        if self.latched:
            self._bind_unit_mgr()
            battle_state = self._battle_squad_state()

            if battle_state is True:
                self._battle_phase = _BATTLE_CONFIRMED
            elif battle_state is False:
                if self._battle_phase == _BATTLE_CONFIRMED:
                    # Do not mistake avatar replacement at battle end for a
                    # real dynamic-platoon leave.
                    if getattr(g_playerEvents, 'isPlayerEntityChanging', False):
                        self._battle_phase = _BATTLE_PENDING
                    else:
                        self.force_off(show_status=True)
                        return
                # False while PENDING is normal during battle loading/teardown.
            else:
                lobby_state = self._lobby_platoon_state()
                if lobby_state:
                    self._battle_phase = _BATTLE_LOBBY
                elif lobby_state is False and self._battle_phase == _BATTLE_LOBBY:
                    # Fallback if a lobby unit-leave event was missed.
                    self.force_off(show_status=True)
                    return
                # PENDING/CONFIRMED + no lobby yet is a normal transition.

            self._keep_mic_open()

        # Recover from a missed key-up or a binding change while the key is held.
        if self.key_down and not self._ptt_down():
            self.key_down = False

        self._ensure_watchdog()

    @staticmethod
    def _set_mic(muted):
        try:
            manager = VOIP.getVOIPManager()
            if not muted:
                if (not manager.isInitialized() or not manager.isEnabled()
                        or not manager.getCurrentChannel()
                        or not manager.isCurrentChannelEnabled()
                        or manager.isInTesting()):
                    return False
            manager.setMicMute(muted=muted)
            return True
        except Exception:
            return False

    def _keep_mic_open(self):
        if self.running and SETTINGS['enabled'] and self.latched:
            self._set_mic(False)

    def _clear_latch_state(self):
        self.latched = False
        self.key_down = False
        self._battle_phase = _BATTLE_LOBBY
        self._unbind_unit_mgr()

    def _manual_toggle(self, controller, original):
        if self.latched:
            self.latched = False
            self._battle_phase = _BATTLE_LOBBY
            self._unbind_unit_mgr()
            result = original(controller, True, True)
            self.show_off_indicator()
            return result

        self.latched = True
        self._battle_phase = (_BATTLE_CONFIRMED if self._battle_squad_state() is True
                              else _BATTLE_LOBBY)
        self._bind_unit_mgr()
        self._ensure_watchdog()
        result = original(controller, False, False)
        self.show_on_indicator()
        return result

    def handle_mute(self, controller, is_muted, force, original):
        if not SETTINGS['enabled']:
            self.key_down = self._ptt_down()
            if not self.key_down:
                self._cancel_watchdog()
            return original(controller, is_muted, force)

        # Once ON, preserve the latch through lobby/battle transition gaps.
        # Current platoon membership is required only to start a new latch.
        if not self.latched and not self._can_toggle_here():
            self.key_down = self._ptt_down()
            if not self.key_down:
                self._cancel_watchdog()
            return original(controller, is_muted, force)

        physical_down = self._ptt_down()

        # Native PTT press edge: WoT asks to unmute while the key is down.
        if physical_down and not self.key_down and not is_muted:
            self.key_down = True
            self._ensure_watchdog()
            return self._manual_toggle(controller, original)

        if physical_down:
            self.key_down = True
            self._ensure_watchdog()
            return original(controller, not self.latched, not self.latched)

        if self.key_down:
            self.key_down = False
            result = original(controller, not self.latched, not self.latched)
            if not self.latched:
                self._cancel_watchdog()
            return result

        # Incidental native mute requests cannot cancel an ON latch.
        if self.latched:
            return original(controller, False, False)

        return original(controller, is_muted, force)

    def force_off(self, show_status):
        was_on = self.latched
        if was_on:
            self._set_mic(True)
        self._clear_latch_state()
        self._cancel_watchdog()

        if show_status and was_on:
            self.show_off_indicator()
        else:
            self.hide_indicator()

    def _create_indicator(self):
        try:
            text = GUI.Text('')
            attrs = (
                ('font', 'system/fonts/default_small.font'),
                ('horizontalPositionMode', 'CLIP'),
                ('verticalPositionMode', 'CLIP'),
                ('widthMode', 'CLIP'),
                ('heightMode', 'CLIP'),
                ('horizontalAnchor', 'CENTER'),
                ('verticalAnchor', 'CENTER'),
                ('position', (0.0, -0.82, 0.1)),
                ('width', 0.7),
                ('height', 0.08),
                ('multiline', False),
                ('focus', False),
            )
            for name, value in attrs:
                setattr(text, name, value)
            self._indicator = text
            return True
        except Exception:
            _logger.exception('Could not create microphone indicator.')
            return False

    def _show_indicator(self, label, colour):
        if not SETTINGS['showIndicator']:
            self.hide_indicator()
            return
        if self._indicator is None and not self._create_indicator():
            return

        try:
            self._indicator.text = label
            self._indicator.colour = colour
            if not self._indicator_added:
                GUI.addRoot(self._indicator)
                self._indicator_added = True
        except Exception:
            _logger.exception('Could not display microphone indicator.')

    def _show_status(self, label, colour):
        self._indicator_token += 1
        token = self._indicator_token
        self._show_indicator(label, colour)

        def hide():
            if token == self._indicator_token:
                self.hide_indicator()

        try:
            BigWorld.callback(STATUS_DISPLAY_SECONDS, hide)
        except Exception:
            pass

    def show_on_indicator(self):
        self._show_status('PLATOON MIC: ON', (128, 255, 128, 255))

    def show_off_indicator(self):
        self._show_status('PLATOON MIC: OFF', (255, 190, 120, 255))

    def hide_indicator(self):
        self._indicator_token += 1
        if self._indicator is None or not self._indicator_added:
            return

        try:
            GUI.delRoot(self._indicator)
        except Exception:
            pass
        self._indicator_added = False

    def refresh_indicator(self):
        if SETTINGS['showIndicator'] and self.latched:
            self.show_on_indicator()
        else:
            self.hide_indicator()


def _install_hook():
    global _original_set_mute, _patched_set_mute
    _original_set_mute = VOIPChatController.setMicrophoneMute
    original = _original_set_mute

    def patched(controller, isMuted, force=False):
        if _manager is None:
            return original(controller, isMuted, force)
        return _manager.handle_mute(controller, isMuted, force, original)

    _patched_set_mute = patched
    VOIPChatController.setMicrophoneMute = patched


def _remove_hook():
    global _original_set_mute, _patched_set_mute
    if (VOIPChatController.setMicrophoneMute is _patched_set_mute
            and _original_set_mute is not None):
        VOIPChatController.setMicrophoneMute = _original_set_mute
    _original_set_mute = None
    _patched_set_mute = None


def init():
    global _manager
    if _manager is not None:
        return

    _register_settings()
    _manager = TogglePTT()
    try:
        _install_hook()
        _manager.start()
    except Exception:
        _logger.exception('%s failed to start.', MOD_NAME)
        try:
            _manager.stop()
        except Exception:
            pass
        _remove_hook()
        _manager = None
        return

    _logger.info('%s v%s started.', MOD_NAME, MOD_VERSION)


def fini():
    global _manager
    manager = _manager
    _manager = None

    if manager is not None:
        try:
            manager.stop()
        except Exception:
            _logger.exception('%s failed to stop cleanly.', MOD_NAME)
    _remove_hook()
