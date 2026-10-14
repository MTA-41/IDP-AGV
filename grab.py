from machine import Pin, PWM, ADC
from utime import sleep
import dht, time


#set PWM
pwm = PWM(Pin(21)) 
pwm.freq(50) #20ms PWM period

print("RIGHT")
pwm.duty_ns(2000000000) #dutyCycle 2ms
