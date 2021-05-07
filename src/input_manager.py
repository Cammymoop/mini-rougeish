import pygame
from pygame.locals import *

class InputManager:
    def __init__(self):
        self.tracked_keys = set()
        self.down_keys = set()
        self.input_focus = ''

        self.buttons = []

    def focus(self, new_focus):
        self.input_focus = new_focus

    def track_key(self, key):
        self.tracked_keys.add(key)

    def make_button(self, button_name, input_focus, keyboard_keys, callback = False, repeat = False):
        for k in keyboard_keys:
            self.track_key(k)
        button = NiceButton(self, button_name, input_focus, keyboard_keys, callback, repeat)
        self.buttons.append(button)
        return button

    def get_button(self, button_name):
        # TODO need to make this take a name and focus or something
        for button in self.buttons:
            if button.name == button_name:
                return button
        return False

    def is_key_down(self, key):
        return key in self.down_keys

    def update(self, events, delta_time):
        for event in events:
            if event.type == KEYDOWN:
                if event.key in self.tracked_keys:
                    self.down_keys.add(event.key)
            if event.type == KEYUP:
                if event.key in self.tracked_keys and event.key in self.down_keys:
                    self.down_keys.remove(event.key)

        for button in self.buttons:
            button.update(delta_time)

class NiceButton:
    def __init__(self, input_manager, name, input_focus, keyboard_keys, pressed_callback = False, do_repeat = False):
        self.im = input_manager
        self.name = name
        self.keyboard_keys = keyboard_keys
        self.input_focus = input_focus

        self.is_down = False
        self.just_pressed = False
        self.just_repeated = False

        self.do_repeats = do_repeat
        self.repeat_delay = 300
        self.repeat_period = 150

        self.repeat_countdown = self.repeat_delay

        self.pressed_callback = pressed_callback

    def do_repeat(self, repeat):
        self.do_repeats = repeat

    def repeat_delay(self, repeat_delay, repeat_period = 0):
        if repeat_period == 0:
            repeat_period = repeat_delay

        self.repeat_delay = repeat_delay
        self.repeat_period = repeat_period

    def set_pressed_callback(self, pressed_callback = False):
        self.pressed_callback = pressed_callback

    def update(self, delta_time):
        if self.just_pressed:
            self.just_pressed = False
        if self.just_repeated:
            self.just_repeated = False

        # Set self to down and dont run callbacks if input focus is not correct
        if self.input_focus and self.input_focus != self.im.input_focus:
            self.is_down = False
            return

        any_down = False
        for k in self.keyboard_keys:
            if self.im.is_key_down(k):
                any_down = True

        if not self.is_down and any_down:
            self.just_pressed = True
            if self.do_repeats:
                self.repeat_countdown = self.repeat_delay
        self.is_down = any_down

        if self.pressed_callback and self.just_pressed:
            self.pressed_callback()

        if self.do_repeats and self.is_down and not self.just_pressed:
            self.repeat_countdown -= delta_time
            if self.repeat_countdown < 0:
                self.just_repeated = True
                self.repeat_countdown += self.repeat_period
                if self.pressed_callback:
                    self.pressed_callback()
