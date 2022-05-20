from enum import Enum
from turtle import position
from gpiozero import PWMLED, Button
from numpy import True_
from stepper import StepperDirections
import time


class Positions(Enum):
    HOME = 'HOME'
    BOTTOM = 'BOTTOM'
    UNKNOWN = 'UNKNOWN'

class Brain(object):
    last_light_change = 0
    last_valid_marker = 0
    last_valid_tract = time.time() - 10
    brightness = 0
    _marker = [0, 0, 0, 0]
    _tract = [0, 0, 0, 0]
    moving = False
    led_direction = True
    action = "Nothing"
    is_new_tract = True

    def __init__(self, stepper):
        self.led = PWMLED(17)

        self.stepper = stepper
        self.stepper.add_home_observer(self.just_got_home)

        self._position = Positions.UNKNOWN
        self._prev_position = Positions.UNKNOWN

        # observers arrays
        self._pos_observers = []

    @property
    def prev_position(self):
        return self._prev_position

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._prev_position = self._position
        self._position = value
        for callback in self._pos_observers:
            print('announcing change')
            callback(self._position)

    def just_got_home(self):
        self.stepper.go_in_mm(1, StepperDirections.DOWN, 100, True)
        self.position = Positions.HOME
        self.moving = False
        self.action = "Just got home"


    def set_tract(self, value):
        x, y, w, h = value
        # wait 10 seconds between tracts
        if x < 50 and y < 20 and (time.time() - self.last_valid_tract > 10) and self._tract[3] == 0:
            print('new tract')
            self.is_new_tract = True
            self.action = "New tract"
        self._tract = [x, y, w, h]

    def set_marker(self, value):
        x, y, w, h = value
        self._marker = [x, y, w, h]

        if y > 30 and x > 300:
            self.position = Positions.BOTTOM
        else:
            self.position = Positions.UNKNOWN if self.prev_position != Positions.HOME else Positions.HOME

    def has_marker(self):
        return self._marker[3] > 0 and self._marker[2] > 0

    def has_tract(self):
        return self._tract[3] > 0 and self._tract[2] > 0

    def increase_brightness(self):
        self.brightness += 1
        if (self.brightness < 100):
            self.led.value = self.brightness / 100
        else:
            self.led_direction = False

    def decrease_brightness(self):
        self.brightness -= 1
        if self.brightness > 0:
            self.led.value = self.brightness / 100
        else:
            self.led_direction = True

    def change_brightness(self):
        self.action = "Changing brightness"
        # # if more than a second has passed since the last change
        # if time.time() - self.last_light_change > 1:
        #     self.last_light_change = time.time()
        #     if self.led_direction:
        #         self.increase_brightness()
        #     else:
        #         self.decrease_brightness()

    def move_until_marker(self):
        self.action = "Moving until marker"
        self.moving = True
        self.stepper.go_in_mm(10, StepperDirections.DOWN, 1000)
        if not self.has_marker:
            self.move_until_marker()
        else:
            self.moving = False

    def process(self):
        self.action = "Processing"
        if not self.has_marker() or not self.has_tract():
            self.change_brightness()

        if not self.moving:
            self.action = "Checking if can move"
            if (self.position == Positions.BOTTOM) and self.has_tract() and self.has_marker() and self.is_new_tract:

                self.action = "Stamp"
                self.moving = True
                self.stepper.go_in_mm(5, StepperDirections.DOWN, 100)
                # time.sleep(1)
                self.stepper.go_in_mm(5, StepperDirections.UP, 100)
                self.stepper.go_home()
                self.moving = False
                self.last_valid_marker = time.time()
                self.is_new_tract = False
                self.last_valid_tract = time.time()

            elif self.position == Positions.UNKNOWN:
                self.moving = True
                self.action = "Going home"
                self.stepper.go_home()
                self.moving = False
            elif self.position == Positions.HOME and self.has_tract() and self.is_new_tract:
                self.action = "Preparing to stamp tract"
                self.moving = True

                self.stepper.go_in_mm(40, StepperDirections.DOWN, 100)

                # self.move_until_marker()
                self.moving = False
            elif not self.has_tract():
                self.action = "Waiting for tract"
        else:
            self.action = "Not moving; movement in progress"
