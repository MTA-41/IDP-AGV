from machine import ADC, Pin
from time import sleep


class DRV5055:
    """Read the analogue output of a DRV5055 on a Raspberry Pi Pico ADC pin."""

    def __init__(self, pin=26, zero_field=41600, deadband=1000):
        # GP26 is ADC0 on the Pico. Change pin to 27 or 28 if wired to ADC1/ADC2.
        self.output = ADC(Pin(pin))
        # The DRV5055 output is approximately half its supply with no magnetic
        # field. Set zero_field from a no-magnet reading if a more exact centre
        # is needed for this sensor and supply.
        self.zero_field = zero_field
        self.deadband = deadband

    def read(self):
        return self.output.read_u16()

    def polarity(self):
        value = self.read()
        difference = value - self.zero_field

        if difference > self.deadband:
            return "positive", value
        if difference < -self.deadband:
            return "negative", value
        return "no field / near zero", value


def get_polarity(sensor):
    """Print the detected output polarity every two seconds, continuously."""
    while True:
        polarity, value = sensor.polarity()
        print("Polarity: {} (ADC: {})".format(polarity, value))
        sleep(2)


magnetometer = DRV5055(pin=26)
get_polarity(magnetometer)
