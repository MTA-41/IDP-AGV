from machine import Pin, PWM, ADC
from utime import sleep
import dht, time

# INSERT LIGHT SENSOR INITIATION
# 18,19,20,21 GPIO numbers

right = Pin(18, Pin.IN),
left = Pin(19, Pin.IN),
forward = Pin(20, Pin.IN),
backward = Pin(21, Pin.IN), 

for i in range(100):
    print(right.value())
    sleep(0.5)

sensor_values = [right.value(), left.value(), forward.value(), backward.value()]