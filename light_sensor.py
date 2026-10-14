from machine import Pin, PWM, ADC
from utime import sleep
import dht, time

# INSERT LIGHT SENSOR INITIATION
# 18,19,20,21 GPIO numbers


for i in range(100):
    right = Pin(18, Pin.IN)
    print(right.value())
    sleep(0.5)

#right = ADC(Pin(24))

# def reading():

#     diff = right - left
#     variable  = front + back + diff

#     if variable != 2:
#         if diff == 1:
#             pass