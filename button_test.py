from machine import Pin
from time import sleep_ms


class Button:
    def __init__(self, pin=11, debounce_ms=30):
        #17
        # Project wiring uses a pull-down: released = 0, pressed = 1.
        self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        self.debounce_ms = debounce_ms

    def was_clicked(self):
        """Return True once per press, and re-arm after the button is released."""
        if self.pin.value() != 1:
            return False

        # Confirm the press and suppress contact bounce.
        sleep_ms(self.debounce_ms)
        if self.pin.value() != 1:
            return False

        # Wait for release so holding the button cannot count as repeated clicks.
        while self.pin.value() == 1:
            sleep_ms(10)
        sleep_ms(self.debounce_ms)
        return True


def get_clicks(button):
    """Continuously print one message for each complete button press."""
    clicks = 0
    while True:
        if button.was_clicked():
            clicks += 1
            print(f"Button clicked: {clicks}")


button = Button(pin=11)
get_clicks(button)
