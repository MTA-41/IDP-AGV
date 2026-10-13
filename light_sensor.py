from machine import Pin, PWM, ADC
from utime import sleep

# INSERT LIGHT SENSOR INITIATION

right = ADC(24)

for i in range(100):
    print(right)
    sleep(0.5)

def reading():

    diff = right - left
    variable  = front + back + diff

    if variable != 2:
        if diff = 1:
            return