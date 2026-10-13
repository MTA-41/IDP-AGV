from machine import Pin, PWM, ADC
from utime import sleep

class Motor:
    def __init__(self, dirPin, PWMPin):
        self.mDir = Pin(dirPin, Pin.OUT)  # set motor direction pin
        self.pwm = PWM(Pin(PWMPin))  # set motor pwm pin
        self.pwm.freq(1000)  # set PWM frequency
        self.pwm.duty_u16(0)  # set duty cycle - 0=off
        
    def off(self):
        self.pwm.duty_u16(0)
        
    def Forward(self, speed=100):
        self.mDir.value(0)                     # forward = 0 reverse = 1 motor
        self.pwm.duty_u16(int(65535 * speed / 100))  # speed range 0-100 motor

    def Reverse(self, speed=30):
        self.mDir.value(1)
        self.pwm.duty_u16(int(65535 * speed / 100))


def create_motors():
    left_motor = Motor(dirPin=4, PWMPin=5)  # Motor is controlled from Motor Driv2 #1, which is on GP4/5
    right_motor = Motor(dirPin=4, PWMPin=5) #change pins for operation

def move_forward(motor_left, motor_right, duration):
    #parameter being a negative value will go back.
    motor_left.forward()
    motor_right.forward()
    sleep(duration)

def turn_left(motor_left, motor_right, duration):
    motor_right.forward()
    sleep(duration)

def turn_right(motor_left, motor_right, duration):
    motor_left.forward()
    sleep(duration)

def actuate_grab():
    pass