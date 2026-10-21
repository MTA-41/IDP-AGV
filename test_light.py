from machine import Pin
from time import sleep


class Light:
    def __init__(self, pin=8):
        # GP8 is the onboard LED pin on a Raspberry Pi Pico.
        self.led = Pin(pin, Pin.OUT)
        self.off()

    def on(self):
        self.led.value(1)

    def off(self):
        self.led.value(0)


def flash(light, interval=0.5):
    """Continuously switch the light on and off."""
    while True:
        light.on()
        print('on')
        sleep(interval)
        light.off()
        print('off')
        sleep(interval)


light = Light(pin=8)
flash(light)
