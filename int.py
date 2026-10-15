from machine import Pin, PWM, ADC
from time import *

#############  motor functions  ###########################
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


def move_forward(motor_left, motor_right, duration):
    motor_left.Forward()
    motor_right.Forward()
    sleep(duration)

def turn_left(motor_left, motor_right, duration):
    motor_left.off()
    motor_right.Forward()
    sleep(duration)

def turn_right(motor_left, motor_right, duration):
    motor_right.off()
    motor_left.Forward()
    sleep(duration)

def move_back(motor_left, motor_right, duration):
    motor_left.Reverse()
    motor_right.Reverse()
    sleep(duration)

############  light sensor function  #######################
def get_light_values(forward, backward, left, right):
    sensor_values = [right.value(), left.value(), forward.value(), backward.value()]
    return sensor_values


###########.  component declaration. #########################

right_light_sensor = Pin(18, Pin.IN)
left_light_sensor = Pin(20, Pin.IN)
front_light_sensor = Pin(19, Pin.IN)
back_light_sensor = Pin(21, Pin.IN)

left_motor = Motor(dirPin=7, PWMPin=6)
right_motor = Motor(dirPin=4, PWMPin=5)






def line_follow():

    go = True
    while go == True:

        right, left, front, back = get_light_values(front_light_sensor, back_light_sensor, left_light_sensor, right_light_sensor)

        if right == 0 and left == 0 and front == 1:
            print('f')
            move_forward(left_motor, right_motor, 0.001)

        elif right == 1 and left == 0 and front == 0:
            print('r')
            turn_right(left_motor, right_motor, 0.001)

        elif right == 0 and left == 1 and front == 0:
            print('l')
            turn_left(left_motor, right_motor, 0.001) 

        elif right == 0 and left == 1 and front == 1:
            print('jun')
            turn_left(left_motor, right_motor, 1)



line_follow()

