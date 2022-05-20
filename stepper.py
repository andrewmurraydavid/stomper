import RPi.GPIO as GPIO
from enum import Enum
from RpiMotorLib import RpiMotorLib
import time
import os
from gpiozero import LED, Button

DIR_pin= 22
STEP_pin = 23
EN_pin = 24


class StepperDirections(Enum):
    DOWN = False
    UP = True

class StepperAdapter(object):
    home_observers = []
    at_home = False

    def __init__(self):
        self.motor = RpiMotorLib.A4988Nema(DIR_pin, STEP_pin, (21,21,21), "DRV8825")
        # self.motor.motor_setup()
        self.prev_at_home = False

        self.revo = 200 * 16

        self.button = Button(2, hold_time=2)

        self.button.when_pressed = self.just_got_home
        self.button.when_held = self.stop_now

        GPIO.setup(EN_pin,GPIO.OUT) # set enable pin as output

    def add_home_observer(self, observer):
        self.home_observers.append(observer)
    
    def just_got_home(self):
        self.at_home = True
        print("Just got home")
        for callback in self.home_observers:
            callback()


    def stop_now(self):
        print("Stopping now")
        GPIO.output(EN_pin,GPIO.HIGH)
        os.abort()

    def go_home(self):
        self.go_in_mm(1, StepperDirections.UP, 10, True)
        if not self.at_home:
            self.go_home()

    def go_in_mm(self, mm, _direction, speed, ignore_home=False):
        if not ignore_home:
            self.at_home = False
        else:
            print("Ignoring home")
        
        debug = False

        delay = 0.000001 / float(speed)

        GPIO.output(EN_pin,GPIO.LOW) # pull enable to low to enable motor
        steps = (mm * self.revo) / 8
        direction = _direction is StepperDirections.UP
        _dir = "UP" if direction is StepperDirections.UP else "DOWN"
        # print(f"Moving {_dir}, {direction}, {mm}mm ")

        self.motor.motor_go(direction, "1/16", int(steps), delay, debug, 0)
