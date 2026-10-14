from machine import Pin, PWM, ADC
from utime import sleep
import dht, time

# INSERT LIGHT SENSOR INITIATION



for i in range(100):
    right = Pin(17, Pin.IN)
    print(right.value())
    sleep(0.5)

#right = ADC(Pin(24))

# def reading():

#     diff = right - left
#     variable  = front + back + diff

#     if variable != 2:
#         if diff == 1:
#             pass