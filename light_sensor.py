from machine import Pin, PWM, ADC
from utime import sleep
import dht, time

# INSERT LIGHT SENSOR INITIATION

right = Pin(25, Pin.IN)

for i in range(100):
    print(right.value())
    sleep(0.5)

# def reading():

#     diff = right - left
#     variable  = front + back + diff

#     if variable != 2:
#         if diff == 1:
#             pass