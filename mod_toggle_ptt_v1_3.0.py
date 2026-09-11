# -*- coding: utf-8 -*-
"""Toggle Push-to-Talk for World of Tanks platoon voice chat."""
from __future__ import absolute_import

import logging
import BigWorld
import CommandMapping
import GUI
import VOIP

from gui.prb_control import prb_getters
from helpers import dependency
from messenger.proto.bw_chat2.VOIPChatController import VOIPChatController
from skeletons.gui.game_control import IPlatoonController

MOD_ID = 'panda_toggle_platoon_ptt'
MOD_NAME = 'Toggle Platoon PTT'
MOD_VERSION = '1.3.0'
SETTINGS_VERSION = 1

WATCHDOG_SECONDS = 0.5
OFF_DISPLAY_SECONDS = 3.0
SETTINGS = {'enabled': True, 'showIndicator': True}

_logger = logging.getLogger(MOD_ID)
_manager = None
_original_set_mute = None
_patched_set_mute = None


def _apply_settings(values):
    if isinstance(values, dict):
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
        _manager.turn_off(show_status=True)
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
                        '{BODY}ON stays visible. OFF disappears after 3 seconds.{/BODY}'
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
        self._was_in_platoon = False
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

    def stop(self):
        if not self.running:
            return
        self.running = False
        self._cancel_watchdog()
        if self.latched:
            self.turn_off(show_status=False)
        else:
            self.key_down = False
            self.hide_indicator()
        self._unbind_unit_mgr()
        try:
            VOIP.getVOIPManager().onJoinedChannel -= self._on_joined_channel
        except Exception:
            pass

    @staticmethod
    def in_platoon():
        try:
            checker = getattr(BigWorld.player(), 'isPlayerInSquad', None)
            if callable(checker):
                return bool(checker())
        except Exception:
            pass
        try:
            controller = dependency.instance(IPlatoonController)
            return bool(controller and controller.isInPlatoon())
        except Exception:
            return False

    @staticmethod
    def _ptt_down():
        try:
            key = CommandMapping.g_instance.get('CMD_VOICECHAT_MUTE')
            return bool(BigWorld.isKeyDown(key))
        except Exception:
            return False

    def _bind_current_unit_mgr(self):
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
        if self._unit_mgr is None:
            return
        try:
            self._unit_mgr.onUnitLeft -= self._on_unit_left
        except Exception:
            pass
        self._unit_mgr = None

    def _on_unit_left(self, unit_mgr_id, is_finished_assembling):
        if self.latched and not is_finished_assembling:
            self.turn_off(show_status=True)

    def _on_joined_channel(self, *args, **kwargs):
        if not self.latched:
            return
        try:
            BigWorld.callback(0.1, self._restore)
        except Exception:
            self._restore()

    def _restore(self):
        if (self.running and SETTINGS['enabled'] and self.latched
                and self.in_platoon() and self._set_mic(False)):
            self.show_on_indicator()

    def _ensure_watchdog(self):
        if (not self.running or self._watchdog_id is not None
                or not (self.latched or self.key_down)):
            return
        try:
            self._watchdog_id = BigWorld.callback(WATCHDOG_SECONDS, self._watchdog)
        except Exception:
            self._watchdog_id = None

    def _cancel_watchdog(self):
        if self._watchdog_id is None:
            return
        try:
            BigWorld.cancelCallback(self._watchdog_id)
        except Exception:
            pass
        self._watchdog_id = None

    def _watchdog(self):
        self._watchdog_id = None
        if not self.running:
            return
        if self.latched:
            self._bind_current_unit_mgr()

            in_platoon = self.in_platoon()
            if in_platoon and not self._was_in_platoon:
                self._restore()
            self._was_in_platoon = in_platoon

            try:
                checker = getattr(BigWorld.player(), 'isPlayerInSquad', None)
                if callable(checker) and not checker():
                    self.turn_off(show_status=True)
                    return
            except Exception:
                pass
        if self.key_down and not self._ptt_down():
            self.key_down = False
        self._ensure_watchdog()

    @staticmethod
    def _set_mic(muted):
        try:
            manager = VOIP.getVOIPManager()
            if not muted and (not manager.getCurrentChannel() or manager.isInTesting()):
                return False
            manager.setMicMute(muted=muted)
            return True
        except Exception:
            return False

    @staticmethod
    def _apply_latch(controller, original, muted):
        return original(controller, muted, bool(muted))

    def handle_mute(self, controller, is_muted, force, original):
        if not SETTINGS['enabled'] or not self.in_platoon():
            self.key_down = self._ptt_down()
            return original(controller, is_muted, force)

        physical_down = self._ptt_down()

        if physical_down and not self.key_down and not is_muted:
            self.key_down = True
            self.latched = not self.latched
            if self.latched:
                self._was_in_platoon = True
                self._bind_current_unit_mgr()
            self._ensure_watchdog()
            result = self._apply_latch(controller, original, not self.latched)
            if self.latched:
                self.show_on_indicator()
            else:
                self.show_off_indicator()
            return result

        if physical_down:
            self.key_down = True
            self._ensure_watchdog()
            return self._apply_latch(controller, original, not self.latched)

        if self.key_down:
            self.key_down = False
            return self._apply_latch(controller, original, not self.latched)

        if self.latched:
            return self._apply_latch(controller, original, False)

        return original(controller, is_muted, force)

    def turn_off(self, show_status):
        was_on = self.latched
        self.latched = False
        self.key_down = False
        self._was_in_platoon = False
        if was_on:
            self._set_mic(True)
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

    def _show_indicator(self, text, colour):
        if not SETTINGS['showIndicator']:
            self.hide_indicator()
            return
        if self._indicator is None and not self._create_indicator():
            return
        try:
            self._indicator.text = text
            self._indicator.colour = colour
            if not self._indicator_added:
                GUI.addRoot(self._indicator)
                self._indicator_added = True
        except Exception:
            _logger.exception('Could not display microphone indicator.')

    def show_on_indicator(self):
        self._indicator_token += 1
        token = self._indicator_token

        self._show_indicator(
            'PLATOON MIC: ON',
            (128, 255, 128, 255)
        )

        def hide():
            if token == self._indicator_token and self.latched:
                self.hide_indicator()

        try:
            BigWorld.callback(OFF_DISPLAY_SECONDS, hide)
        except Exception:
            pass

    def show_off_indicator(self):
        self._indicator_token += 1
        token = self._indicator_token
        self._show_indicator('PLATOON MIC: OFF', (255, 190, 120, 255))

        def hide():
            if token == self._indicator_token and not self.latched:
                self.hide_indicator()

        try:
            BigWorld.callback(OFF_DISPLAY_SECONDS, hide)
        except Exception:
            pass

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
