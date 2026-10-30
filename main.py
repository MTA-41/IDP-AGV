from machine import Pin, PWM, I2C, ADC, Timer
from micropython import const
from time import *
from collections import deque
import utime
import ustruct

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
        #print("Polarity: {} (ADC: {})".format(polarity, value))
        sleep(2)


# ======================================================================
# MOTOR CLASS
# ======================================================================
class Motor:
    def __init__(self, dirPin, PWMPin):
        self.mDir = Pin(dirPin, Pin.OUT)
        self.pwm = PWM(Pin(PWMPin))
        self.pwm.freq(1000)
        self.pwm.duty_u16(0)

    def off(self):
        self.pwm.duty_u16(0)

    def Forward(self, speed=100):
        self.mDir.value(1)
        self.pwm.duty_u16(int(65535 * speed / 100))

    def Reverse(self, speed=100):
        self.mDir.value(0)
        self.pwm.duty_u16(int(65535 * speed / 100))


# ======================================================================
# SERVO CLASS
# ======================================================================

class Servo():
    # Common settings for 270° servos:
    # 0.5 ms → minimum (0°)
    # 2.5 ms → maximum (270°)
    # Total span = 2.0 ms
    # Frequency: 50 Hz (20 ms period)
    # 
    # Duty % = Pulse width / Period x 100
    # Minimum (0°) = 0.5/20
    # Centre (135°) = 1.5/20
    # Maximum (270°) = 2.5/20
    #
    # Convert to Pico PWM (16-bit)
    # Pico uses: 0 → 65535
    # Duty value = Duty Fraction x 65535
    # Minimum (0.5 ms) = 0.025 * 65535
    # Centre (1.5 ms) = 0.075 * 65535
    # Maximum (2.5 ms) = 0.0125 * 65535
    MIN_DUTY = 1638 # 0°
    MID_DUTY = 4915 # 135°
    MAX_DUTY = 8192 # 270°
    
    def __init__(self, ServoPin):
        self.servo = PWM(ServoPin)
        self.servo.freq(50)  # 50 Hz for servo
 
    # Convert angle (0–270) to duty
    def set_angle(self, angle):
       # Clamp angle
       if angle < 0:
           angle = 0
       if angle > 270:
           angle = 270
 
       duty = int(Servo.MIN_DUTY + (angle / 270) * (Servo.MAX_DUTY - Servo.MIN_DUTY))
       self.servo.duty_u16(duty)



# ======================================================================
# VL53L0X CONSTANTS AND CLASS
# Retained from your original code.
# Navigation does not use this driver.
# ======================================================================
_IO_TIMEOUT = 1000
_SYSRANGE_START = const(0x00)
_EXTSUP_HV = const(0x89)
_MSRC_CONFIG = const(0x60)
_FINAL_RATE_RTN_LIMIT = const(0x44)
_SYSTEM_SEQUENCE = const(0x01)
_SPAD_REF_START = const(0x4f)
_SPAD_ENABLES = const(0xb0)
_REF_EN_START_SELECT = const(0xb6)
_SPAD_NUM_REQUESTED = const(0x4e)
_INTERRUPT_GPIO = const(0x0a)
_INTERRUPT_CLEAR = const(0x0b)
_GPIO_MUX_ACTIVE_HIGH = const(0x84)
_RESULT_INTERRUPT_STATUS = const(0x13)
_RESULT_RANGE_STATUS = const(0x14)
_OSC_CALIBRATE = const(0xf8)
_MEASURE_PERIOD = const(0x04)

SYSRANGE_START = 0x00
SYSTEM_SEQUENCE_CONFIG = 0x01
SYSTEM_INTERRUPT_CLEAR = 0x0B
RESULT_INTERRUPT_STATUS = 0x13

PRE_RANGE_CONFIG_VALID_PHASE_LOW = 0x56
PRE_RANGE_CONFIG_VALID_PHASE_HIGH = 0x57
PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x51
MSRC_CONFIG_TIMEOUT_MACROP = 0x46

FINAL_RANGE_CONFIG_VALID_PHASE_LOW = 0x47
FINAL_RANGE_CONFIG_VALID_PHASE_HIGH = 0x48
FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70
FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x71

GLOBAL_CONFIG_VCSEL_WIDTH = 0x32
ALGO_PHASECAL_LIM = 0x30
ALGO_PHASECAL_CONFIG_TIMEOUT = 0x30

class TimeoutError(RuntimeError):
    pass


class VL53L0X:
    def __init__(self, i2c, address=0x29):
        self.i2c = i2c
        self.address = address
        self._started = False
        self._stop_variable = 0
        self.measurement_timing_budget_us = 20000
        self.enables = {
            "tcc": 0, "dss": 0, "msrc": 0,
            "pre_range": 0, "final_range": 0
        }
        self.timeouts = {
            "pre_range_vcsel_period_pclks": 0,
            "msrc_dss_tcc_mclks": 0,
            "msrc_dss_tcc_us": 0,
            "pre_range_mclks": 0,
            "pre_range_us": 0,
            "final_range_vcsel_period_pclks": 0,
            "final_range_mclks": 0,
            "final_range_us": 0
        }
        self.vcsel_period_type = [
            "VcselPeriodPreRange",
            "VcselPeriodFinalRange"
        ]
        self.init()

    def _registers(self, register, values=None, struct="B"):
        if values is None:
            size = ustruct.calcsize(struct)
            data = self.i2c.readfrom_mem(self.address, register, size)
            return ustruct.unpack(struct, data)

        data = ustruct.pack(struct, *values)
        self.i2c.writeto_mem(self.address, register, data)

    def _register(self, register, value=None, struct="B"):
        if value is None:
            return self._registers(register, struct=struct)[0]
        self._registers(register, (value,), struct=struct)

    def _flag(self, register=0x00, bit=0, value=None):
        data = self._register(register)
        mask = 1 << bit

        if value is None:
            return bool(data & mask)

        if value:
            data |= mask
        else:
            data &= ~mask

        self._register(register, data)

    def _config(self, *config):
        for register, value in config:
            self._register(register, value)

    def init(self, power2v8=True):
        self._flag(_EXTSUP_HV, 0, power2v8)

        self._config(
            (0x88, 0x00),
            (0x80, 0x01),
            (0xff, 0x01),
            (0x00, 0x00)
        )
        self._stop_variable = self._register(0x91)
        self._config(
            (0x00, 0x01),
            (0xff, 0x00),
            (0x80, 0x00)
        )

        self._flag(_MSRC_CONFIG, 1, True)
        self._flag(_MSRC_CONFIG, 4, True)
        self._register(
            _FINAL_RATE_RTN_LIMIT,
            int(0.1 * (1 << 7)),
            struct=">H"
        )
        self._register(_SYSTEM_SEQUENCE, 0xff)

        spad_count, is_aperture = self._spad_info()
        spad_map = bytearray(
            self._registers(_SPAD_ENABLES, struct="6B")
        )

        self._config(
            (0xff, 0x01),
            (_SPAD_REF_START, 0x00),
            (_SPAD_NUM_REQUESTED, 0x2c),
            (0xff, 0x00),
            (_REF_EN_START_SELECT, 0xb4)
        )

        spads_enabled = 0
        for i in range(48):
            if (
                (i < 12 and is_aperture)
                or spads_enabled >= spad_count
            ):
                spad_map[i // 8] &= ~(1 << (i % 8))
            elif spad_map[i // 8] & (1 << (i % 8)):
                spads_enabled += 1

        self._registers(_SPAD_ENABLES, spad_map, struct="6B")

        self._config(
            (0xff, 0x01), (0x00, 0x00),
            (0xff, 0x00), (0x09, 0x00),
            (0x10, 0x00), (0x11, 0x00),
            (0x24, 0x01), (0x25, 0xFF),
            (0x75, 0x00), (0xFF, 0x01),
            (0x4E, 0x2C), (0x48, 0x00),
            (0x30, 0x20), (0xFF, 0x00),
            (0x30, 0x09), (0x54, 0x00),
            (0x31, 0x04), (0x32, 0x03),
            (0x40, 0x83), (0x46, 0x25),
            (0x60, 0x00), (0x27, 0x00),
            (0x50, 0x06), (0x51, 0x00),
            (0x52, 0x96), (0x56, 0x08),
            (0x57, 0x30), (0x61, 0x00),
            (0x62, 0x00), (0x64, 0x00),
            (0x65, 0x00), (0x66, 0xA0),
            (0xFF, 0x01), (0x22, 0x32),
            (0x47, 0x14), (0x49, 0xFF),
            (0x4A, 0x00), (0xFF, 0x00),
            (0x7A, 0x0A), (0x7B, 0x00),
            (0x78, 0x21), (0xFF, 0x01),
            (0x23, 0x34), (0x42, 0x00),
            (0x44, 0xFF), (0x45, 0x26),
            (0x46, 0x05), (0x40, 0x40),
            (0x0E, 0x06), (0x20, 0x1A),
            (0x43, 0x40), (0xFF, 0x00),
            (0x34, 0x03), (0x35, 0x44),
            (0xFF, 0x01), (0x31, 0x04),
            (0x4B, 0x09), (0x4C, 0x05),
            (0x4D, 0x04), (0xFF, 0x00),
            (0x44, 0x00), (0x45, 0x20),
            (0x47, 0x08), (0x48, 0x28),
            (0x67, 0x00), (0x70, 0x04),
            (0x71, 0x01), (0x72, 0xFE),
            (0x76, 0x00), (0x77, 0x00),
            (0xFF, 0x01), (0x0D, 0x01),
            (0xFF, 0x00), (0x80, 0x01),
            (0x01, 0xF8), (0xFF, 0x01),
            (0x8E, 0x01), (0x00, 0x01),
            (0xFF, 0x00), (0x80, 0x00)
        )

        self._register(_INTERRUPT_GPIO, 0x04)
        self._flag(_GPIO_MUX_ACTIVE_HIGH, 4, False)
        self._register(_INTERRUPT_CLEAR, 0x01)
        self._register(_SYSTEM_SEQUENCE, 0x01)
        self._calibrate(0x40)
        self._register(_SYSTEM_SEQUENCE, 0x02)
        self._calibrate(0x00)
        self._register(_SYSTEM_SEQUENCE, 0xe8)

    def _spad_info(self):
        self._config(
            (0x80, 0x01), (0xff, 0x01),
            (0x00, 0x00), (0xff, 0x06)
        )
        self._flag(0x83, 3, True)
        self._config(
            (0xff, 0x07), (0x81, 0x01),
            (0x80, 0x01), (0x94, 0x6b),
            (0x83, 0x00)
        )

        for _ in range(_IO_TIMEOUT):
            if self._register(0x83):
                break
            utime.sleep_ms(1)
        else:
            raise TimeoutError("SPAD information timeout")

        self._register(0x83, 0x01)
        value = self._register(0x92)
        self._config(
            (0x81, 0x00), (0xff, 0x06)
        )
        self._flag(0x83, 3, False)
        self._config(
            (0xff, 0x01), (0x00, 0x01),
            (0xff, 0x00), (0x80, 0x00)
        )

        return value & 0x7f, bool(value & 0x80)

    def _calibrate(self, vhv_init_byte):
        self._register(_SYSRANGE_START, 0x01 | vhv_init_byte)

        for _ in range(_IO_TIMEOUT):
            if self._register(_RESULT_INTERRUPT_STATUS) & 0x07:
                break
            utime.sleep_ms(1)
        else:
            raise TimeoutError("Calibration timeout")

        self._register(_INTERRUPT_CLEAR, 0x01)
        self._register(_SYSRANGE_START, 0x00)

    def start(self, period=0):
        self._config(
            (0x80, 0x01), (0xFF, 0x01),
            (0x00, 0x00), (0x91, self._stop_variable),
            (0x00, 0x01), (0xFF, 0x00),
            (0x80, 0x00)
        )

        if period:
            oscillator = self._register(_OSC_CALIBRATE, struct=">H")
            if oscillator:
                period *= oscillator
            self._register(_MEASURE_PERIOD, period, struct=">H")
            self._register(_SYSRANGE_START, 0x04)
        else:
            self._register(_SYSRANGE_START, 0x02)

        self._started = True

    def stop(self):
        self._register(_SYSRANGE_START, 0x01)
        self._config(
            (0xFF, 0x01), (0x00, 0x00),
            (0x91, self._stop_variable), (0x00, 0x01),
            (0xFF, 0x00)
        )
        self._started = False

    def read(self):
        if not self._started:
            self.start()

        for _ in range(_IO_TIMEOUT):
            if self._register(_RESULT_INTERRUPT_STATUS) & 0x07:
                break
            utime.sleep_ms(1)
        else:
            raise TimeoutError("Range read timeout")

        value = self._register(_RESULT_RANGE_STATUS + 10, struct=">H")
        self._register(_INTERRUPT_CLEAR, 0x01)
        return value

    def decode_Vcsel_period(self, reg_val):
        return (reg_val + 1) << 1

    def encode_Vcsel_period(self, period_pclks):
        return (period_pclks >> 1) - 1

    def set_Vcsel_pulse_period(self, period_type, period_pclks):
        vcsel_period_reg = self.encode_Vcsel_period(period_pclks)

        if period_type == self.vcsel_period_type[0]:
            if period_pclks not in (12, 14, 16, 18):
                return False

            phase_high = {
                12: 0x18, 14: 0x30,
                16: 0x40, 18: 0x50
            }[period_pclks]

            self._register(PRE_RANGE_CONFIG_VALID_PHASE_HIGH, phase_high)
            self._register(PRE_RANGE_CONFIG_VALID_PHASE_LOW, 0x08)
            self._register(PRE_RANGE_CONFIG_VCSEL_PERIOD, vcsel_period_reg)

        elif period_type == self.vcsel_period_type[1]:
            if period_pclks not in (8, 10, 12, 14):
                return False

            phase_high = {
                8: 0x10, 10: 0x28,
                12: 0x38, 14: 0x48
            }[period_pclks]

            self._register(FINAL_RANGE_CONFIG_VALID_PHASE_HIGH, phase_high)
            self._register(FINAL_RANGE_CONFIG_VALID_PHASE_LOW, 0x08)
            self._register(FINAL_RANGE_CONFIG_VCSEL_PERIOD, vcsel_period_reg)

        else:
            return False

        return True


class Button:
    def __init__(self, pin=10, debounce_ms=30):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
        self.debounce_ms = debounce_ms
        self.click_count = 0

    def was_clicked(self):
        # Wait for a press
        if self.pin.value() != 1:
            return False

        sleep_ms(self.debounce_ms)

        # Confirm the press wasn't contact bounce
        if self.pin.value() != 1:
            return False

        # Count exactly one click
        self.click_count += 1
        #print("[BUTTON] Click count:", self.click_count)

        # Wait for release before accepting another click
        while self.pin.value() == 1:
            sleep_ms(10)

        sleep_ms(self.debounce_ms)
        return True

    def is_on(self):
        # Odd = ON; even = OFF
        return self.click_count % 2 == 1
    
# ======================================================================
# COMPONENTS
# ======================================================================
button = Button(pin=11, debounce_ms=30)
right_light_sensor = Pin(12, Pin.IN)
left_light_sensor = Pin(20, Pin.IN)
front_light_sensor = Pin(19, Pin.IN)
back_light_sensor = Pin(21, Pin.IN)

left_motor = Motor(dirPin=4, PWMPin=5)
right_motor = Motor(dirPin=7, PWMPin=6)

magnetometer = DRV5055(pin=26)


red_led = Pin(9, Pin.OUT)      # on while carrying a NEGATIVE box (top level)
green_led = Pin(10, Pin.OUT)    # on while carrying a POSITIVE box (bottom level)

RIGHT_DEPOT_NODES = {3, 5}      # 20 and 22 are the left-side depots
box_polarity = None             # "positive", "negative" or None
box_row = None                  # row of DELIVERY_BAYS/storage for the held box

#MAG def set_box_leds(polarity):
#MAG     red_led.value(1 if polarity == "negative" else 0)
#MAG     green_led.value(1 if polarity == "positive" else 0)
#MAG
#MAG set_box_leds(None)               # both off at startup
#MAG
#MAG def read_box_polarity():
#MAG     """Average 10 ADC samples so one noisy read can't misclassify the box."""
#MAG     total = 0
#MAG     for _ in range(10):
#MAG         total += magnetometer.read()
#MAG         sleep_ms(5)
#MAG     difference = total // 10 - magnetometer.zero_field
#MAG     if difference > magnetometer.deadband:
#MAG         return "positive"
#MAG     if difference < -magnetometer.deadband:
#MAG         return "negative"
#MAG     return None                  # no magnet: treated as bottom level, no LED
#MAG
#MAG def choose_bay_row(polarity, depot_node):
#MAG     right = depot_node in RIGHT_DEPOT_NODES
#MAG     if polarity == "negative":   # top level
#MAG         return 3 if right else 2
#MAG     return 0 if right else 1     # positive (or non-magnetic): bottom level
#MAG
#MAG def next_bay_in_row(row):
#MAG     global active_delivery
#MAG     for col in range(len(storage[row])):
#MAG         if storage[row][col] == 0:
#MAG             node = DELIVERY_BAYS[row][col]
#MAG             active_delivery = (row, col, node)
#MAG             print("[DELIVERY] Magnetic sort -> row", row, "node", node)
#MAG             return node
#MAG     active_delivery = None
#MAG     print("[DELIVERY ERROR] Row", row, "is full")
#MAG     return None

# ======================================================================
# SETTINGS AND STATE
# ======================================================================
forward, backward, left, right = (
    "forward", "backward", "left", "right"
)

SCAN_GRAB_FOLLOW_MS = 750
STOP_SECONDS = 2
SCAN_DROP_FOLLOW_MS = 3400
JUNCTION_CONFIRM = 3
JUNCTION_CLEAR = 20
BOX_CONFIRM = 3
BOX_RETURNS_EVENT = True

junction_armed = True
junction_reads = 0
clear_reads = 0
box_armed = True
box_reads = 0
bay_armed = True

state = "to depot"
prev_node = None
curr_node = 0
imminent_next_node = 0
target = None
need_pick = True
halted = False

operate_right_side = True
grab = False
box_present = False
filled_bay = False

storage = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0]
]

DELIVERY_BAYS = [
    [7, 9, 11, 13, 15, 17],
    [24, 26, 28, 30, 32, 34],
    [37, 40, 43, 46, 49, 52],
    [38, 41, 44, 47, 50, 53]
]

DELIVERY_BAY_SET = {
    node for row in DELIVERY_BAYS for node in row
}

current_depot = 0
delivery_cursor = 0
active_delivery = None

DEPOT_NODES = [3, 5, 20, 22]


# ======================================================================
# MOTOR MOVEMENT FUNCTIONS
# ======================================================================
def move_forward(motor_left, motor_right, duration):
    #print("[MOVE] Forward | duration:", duration)
    motor_left.Forward()
    motor_right.Forward()
    sleep(duration)


def turn_left(motor_left, motor_right, duration):
    #print("[MOVE] Line correction left | duration:", duration)
    motor_left.off()
    motor_right.Forward()
    sleep(duration)


def turn_right(motor_left, motor_right, duration):
    #print("[MOVE] Line correction right | duration:", duration)
    motor_right.off()
    motor_left.Forward()
    sleep(duration)


def move_back(motor_left, motor_right, duration):
    #print("[MOVE] Reverse | duration:", duration)
    motor_left.Reverse()
    motor_right.Reverse()
    sleep(duration)


def rotateacw90(motor_left, motor_right, duration=0.9):
    global current_direction
    current_direction -= 1
    current_direction = current_direction % 4
    motor_right.off()
    motor_left.off()
    move_forward(motor_left, motor_right, 0.6)
    motor_left.off()
    motor_right.off()
    sleep(2)
    motor_right.Forward()
    #print('rr')
    motor_left.Reverse()
    #print('rl')
    sleep(duration)                 # CHANGED: the rotation never waited, so it never turned
    motor_right.off()
    motor_left.off()
 
def rotatecw90(motor_left, motor_right, duration=0.8):
    global current_direction
    current_direction += 1
    current_direction = current_direction % 4
    motor_right.off()
    motor_left.off()
    move_forward(motor_left, motor_right, 0.6)
    motor_right.off()
    motor_left.off()
    sleep(2)
    motor_left.Forward()
    #print('rl')
    motor_right.Reverse()
    #print('rr')
    sleep(duration)                 # CHANGED: same fix as above
    motor_right.off()
    motor_left.off()

def u_turn(motor_left, motor_right):
    global current_direction
    current_direction += 2
    #print("[MOVE] U-turn started")
    left_motor.off()
    right_motor.off()
    #move_back(left_motor, right_motor, 0.5)
    motor_left.Forward()
        #print('rl')
    motor_right.Reverse()
        #print('rr')
    sleep(1.7)
    #print("[MOVE] U-turn completed")


def stop_and_wait():
    #print("[MOVE] Stop for", STOP_SECONDS, "seconds")
    left_motor.off()
    right_motor.off()
    sleep(STOP_SECONDS)


# ======================================================================
# SENSORS AND GRABBER
# ======================================================================
def get_light_values(forward_sensor, backward_sensor, left_sensor, right_sensor):
    return [
        right_sensor.value(),
        left_sensor.value(),
        forward_sensor.value(),
        backward_sensor.value()
    ]

servo1 = Servo(Pin(13)) 

def arm_down():

    #print("Move to 0°")
    servo1.set_angle(20)

 
def arm_up30():

    #print("Move to 30°")
    servo1.set_angle(0)


def arm_up90():

    #print("Move to 90°")
    servo1.set_angle(-50)




servo_grab = Servo(Pin(15))

def grab_in():

    #print("Grab Move to 0°")
    servo_grab.set_angle(115)

def grab_out30():

    #print("Grab Move to 30°")
    servo_grab.set_angle(100)

def grab_out60():

    #print("Grab Move to 60°")
    servo_grab.set_angle(35)




def line_follow_step():
    right, left, front, back = get_light_values(front_light_sensor, back_light_sensor, left_light_sensor, right_light_sensor)
     
    # ----- driving -----
    if right == 0 and left == 0 and front == 1:
        #print('f')
        move_forward(left_motor, right_motor, 0.001)
    
    elif right == 1 and left == 0 and front == 0:
        #print('r')
        turn_right(left_motor, right_motor, 0.001)
    
    elif right == 0 and left == 1 and front == 0:
        #print('l')
        turn_left(left_motor, right_motor, 0.001)

def scan_grab():
    arm_down()
    grab_out60()
    #print('Scanning for box')
    scan = True

### DISTANCE TO BOX ###
    while scan == True:
        #distance = get_distance()
        #if distance <= 40:
        line_follow_for_ms(SCAN_GRAB_FOLLOW_MS)
        right_motor.off()
        left_motor.off()
        #print('grab code')
        sleep(3)
        arm_up90()
        grab_out60()
        #move_forward(left_motor, right_motor, 0.06)
        right_motor.off()
        left_motor.off()
        arm_down()
        sleep(1)
        grab_in()
        sleep(0.5)
        arm_up30()
        scan = False


        #else:
            #scan = True
            #line_follow_step()

def line_follow_for_ms(duration_ms):
    """Follow the line for a fixed duration without processing junction events."""
    start = utime.ticks_ms()

    while utime.ticks_diff(utime.ticks_ms(), start) < duration_ms:
        line_follow_step()
        utime.sleep_ms(1)

    left_motor.off()
    right_motor.off()

def scan_drop():
    #arm_down()
    #grab_in()
    #print('Scanning for empty space')
    scan = True
    line_follow_for_ms(SCAN_DROP_FOLLOW_MS)


### DISTANCE TO BOX ###
    while scan == True:
        #distance = get_distance()
        #if distance <= 40:
        #line_follow_for_ms(SCAN_DROP_FOLLOW_MS)
        right_motor.off()
        left_motor.off()
        #print('grab code')
        #sleep(3)
        #arm_down()
        sleep(1)
        #move_forward(left_motor, right_motor, 0.1)
        grab_out30()
        sleep(0.5)
        move_back(left_motor, right_motor, 0.8)
        arm_up90()
        scan = False

        #else:
            #line_follow_step()


def get_distance():
    i2c_bus = I2C(id=0, sda=Pin(8), scl=Pin(9))
    vl53l0 = VL53L0X(i2c_bus)
    vl53l0.start()
    distance = vl53l0.read()
    vl53l0.stop()
    return distance


def test_vl53l0x():
    i2c_bus = I2C(id=0, sda=Pin(8), scl=Pin(9))
    vl53l0 = VL53L0X(i2c_bus)

    while True:
        vl53l0.start()
        for _ in range(10):
            #print(vl53l0.read(), "mm")
            sleep(0.5)
        vl53l0.stop()


# ======================================================================
# BOARD GRAPH
# ======================================================================
board_graph = {
    0:  {forward: 35, backward: None, left: 18, right: 1},
    18: {forward: None, backward: None, left: 55, right: 0},
    1:  {forward: None, backward: None, left: 0, right: 54},

    2:  {forward: 4, backward: 54, left: 3, right: None},
    3:  {forward: None, backward: None, left: None, right: 2},
    4:  {forward: 6, backward: 2, left: 5, right: None},
    5:  {forward: None, backward: None, left: None, right: 4},
    6:  {forward: 8, backward: 4, left: 7, right: None},
    7:  {forward: None, backward: None, left: None, right: 6},
    8:  {forward: 10, backward: 6, left: 9, right: None},
    9:  {forward: None, backward: None, left: None, right: 8},
    10: {forward: 12, backward: 8, left: 11, right: None},
    11: {forward: None, backward: None, left: None, right: 10},
    12: {forward: 14, backward: 10, left: 13, right: None},
    13: {forward: None, backward: None, left: None, right: 12},
    14: {forward: 16, backward: 12, left: 15, right: None},
    15: {forward: None, backward: None, left: None, right: 14},
    16: {forward: None, backward: 14, left: 17, right: None},
    17: {forward: None, backward: None, left: None, right: 16},

    19: {forward: 21, backward: 55, left: None, right: 20},
    20: {forward: None, backward: None, left: 19, right: None},
    21: {forward: 23, backward: 19, left: None, right: 22},
    22: {forward: None, backward: None, left: 21, right: None},
    23: {forward: 25, backward: 21, left: None, right: 24},
    24: {forward: None, backward: None, left: 23, right: None},
    25: {forward: 27, backward: 23, left: None, right: 26},
    26: {forward: None, backward: None, left: 25, right: None},
    27: {forward: 29, backward: 25, left: None, right: 28},
    28: {forward: None, backward: None, left: 27, right: None},
    29: {forward: 31, backward: 27, left: None, right: 30},
    30: {forward: None, backward: None, left: 29, right: None},
    31: {forward: 33, backward: 29, left: None, right: 32},
    32: {forward: None, backward: None, left: 31, right: None},
    33: {forward: None, backward: 31, left: None, right: 34},
    34: {forward: None, backward: None, left: 33, right: None},

    35: {forward: 36, backward: 0, left: None, right: None},
    36: {forward: 39, backward: 35, left: 37, right: 38},
    37: {forward: None, backward: None, left: None, right: 36},
    38: {forward: None, backward: None, left: 36, right: None},
    39: {forward: 42, backward: 36, left: 40, right: 41},
    40: {forward: None, backward: None, left: None, right: 39},
    41: {forward: None, backward: None, left: 39, right: None},
    42: {forward: 45, backward: 39, left: 43, right: 44},
    43: {forward: None, backward: None, left: None, right: 42},
    44: {forward: None, backward: None, left: 42, right: None},
    45: {forward: 48, backward: 42, left: 46, right: 47},
    46: {forward: None, backward: None, left: None, right: 45},
    47: {forward: None, backward: None, left: 45, right: None},
    48: {forward: 51, backward: 45, left: 49, right: 50},
    49: {forward: None, backward: None, left: None, right: 48},
    50: {forward: None, backward: None, left: 48, right: None},
    51: {forward: None, backward: 48, left: 52, right: 53},
    52: {forward: None, backward: None, left: None, right: 51},
    53: {forward: None, backward: None, left: 51, right: None},
    54: {forward: 2, backward: None, left: 1, right: None},
    55: {forward: 19, backward: None, left: None, right: 18}
}

ORDER = [forward, right, backward, left]
current_direction = 0 #0 = forward, 1 = right, 2 = backward, 3 = left

# ======================================================================
# PATH FINDING AND TURN DECISIONS
# ======================================================================
def find_path(graph, curr_node, target):
    #print("[PATH] Searching:", curr_node, "->", target)

    if curr_node not in graph or target not in graph:
        #print("[PATH ERROR] Start or target missing from graph")
        return None

    if curr_node == target:
        #print("[PATH] Already at target")
        return [curr_node]

    parents = {curr_node: None}
    queue = deque((), 64)        # MicroPython: iterable must be empty, maxlen is required
    queue.append(curr_node) 

    while queue:
        node = queue.popleft()

        for neighbour in graph[node].values():
            if neighbour is None or neighbour in parents:
                continue
            if neighbour not in graph:
                continue

            parents[neighbour] = node

            if neighbour == target:
                path = [neighbour]
                while parents[path[-1]] is not None:
                    path.append(parents[path[-1]])
                path.reverse()
                #print("[PATH] Found:", path)
                return path

            queue.append(neighbour)

    #print("[PATH ERROR] No path found")
    return None


def next_node(graph, current, target):
    path = find_path(graph, current, target)

    if path is None or len(path) < 2:
        #print("[PATH] No next node")
        return None

    #print("[PATH] Next node:", path[1])
    return path[1]


def next_direction(graph, current, target):
    nxt = next_node(graph, current, target)

    if nxt is None:
        return None

    for direction, neighbour in graph[current].items():
        if neighbour == nxt:
            return direction

    return None

def turn_needed(prev, curr, nxt):
    """
    Uses globally fixed directions and current_direction.

    current_direction:
    0 = forward / north
    1 = right / east
    2 = backward / south
    3 = left / west

    Returns:
    0 = straight
    1 = right
    2 = U-turn
    3 = left
    """
    print(
        "[TURN] Current node:", curr,
        "| Next node:", nxt,
        "| Current direction:", current_direction
    )

    if curr not in board_graph:
        raise ValueError("Current node is not in the board graph")

    if nxt not in board_graph:
        raise ValueError("Next node is not in the board graph")

    # Find the absolute direction of the edge to the next node.
    next_direction = None

    for i in range(4):
        direction = ORDER[i]

        if board_graph[curr][direction] == nxt:
            next_direction = i
            break

    if next_direction is None:
        #print("[TURN ERROR] Next node is not connected to current node")
        raise ValueError("Next node is not connected to current node")

    # Compare the absolute direction with the robot's current orientation.
    turn = (next_direction - current_direction) % 4

    names = ["STRAIGHT", "RIGHT", "U-TURN", "LEFT"]

    # print(
    #     "[TURN] Required absolute direction:", ORDER[next_direction],
    #     "| Decision:", names[turn]
    # )

    return turn
# ======================================================================
# DEPOT AND DELIVERY BOOKKEEPING
# ======================================================================
def next_depot():
    node = DEPOT_NODES[current_depot]
    #print("[TARGET] Next depot:", node)
    return node


def depot_collected():
    global current_depot

    print("[DEPOT] Collection recorded at:", DEPOT_NODES[current_depot])
    current_depot = (current_depot + 1) % len(DEPOT_NODES)
    print("[DEPOT] Next depot index:", current_depot)


def next_delivery_bay():
    global delivery_cursor, active_delivery
    #MAG     if box_row is not None:
    #MAG         return next_bay_in_row(box_row)
    total_cells = len(storage) * len(storage[0])

    print("[DELIVERY] Searching for an empty bay")

    for offset in range(total_cells):
        cell = (delivery_cursor + offset) % total_cells
        depot_index, storage_index = divmod(cell, len(storage[0]))

        if storage[depot_index][storage_index] == 0:
            node = DELIVERY_BAYS[depot_index][storage_index]

            active_delivery = (
                depot_index,
                storage_index,
                node
            )

            delivery_cursor = (cell + 1) % total_cells

            # print(
            #     "[DELIVERY] Selected node:", node,
            #     "| Row:", depot_index,
            #     "| Column:", storage_index
            # )
            return node

    active_delivery = None
    #print("[DELIVERY ERROR] All bays are full")
    return None


def delivery_completed():
    global active_delivery

    if active_delivery is None:
        #print("[DELIVERY WARNING] No active delivery")
        return False

    depot_index, storage_index, node = active_delivery
    storage[depot_index][storage_index] = 1
    active_delivery = None

    #print("[DELIVERY] Completed at node:", node)
    #print("[DELIVERY] Storage:", storage)
    return True


def update_state_machine():
    global state

    old_state = state

    if state == "to depot":
        state = "delivery"
    elif state == "delivery":
        state = "to home"
    elif state == "to home":
        state = "to depot"

    #print("[STATE]", old_state, "->", state)


def pick_target():
    #print("[TARGET] Picking target for state:", state)

    if state == "to depot":
        return next_depot()

    if state == "delivery":
        return next_delivery_bay()

    if state == "to home":
        #print("[TARGET] Home node: 0")
        return 0

    #print("[TARGET ERROR] Unknown state:", state)
    return None


# ======================================================================
# TARGET ARRIVAL AND HALTING
# ======================================================================
def arrive_at_target():
    global target

    #print("[ARRIVAL] Reached target:", target, "| State:", state)

    if state == "to depot":
        stop_and_wait()
        # grabber_down() / grabber_up() would go here
        depot_collected()

    elif state == "delivery":
        stop_and_wait()
        # Release the box here.
        delivery_completed()

    # elif state == "to home":
    #     print("[HOME] Returned to start node")

    update_state_machine()
    target = pick_target()

    #print("[TARGET] New target:", target)


def halt(reason):
    global halted

    left_motor.off()
    right_motor.off()
    halted = True

    #print("[HALT]", reason)


def perform_turn(turn):
    names = ["STRAIGHT", "RIGHT", "U-TURN", "LEFT"]

    if turn not in (0, 1, 2, 3):
        halt("Invalid turn decision: " + str(turn))
        return

    #print("[MOVEMENT DECISION] Executing:", names[turn])

    if turn == 0:
        move_forward(left_motor, right_motor, 0.01)
    elif turn == 1:
        rotatecw90(left_motor, right_motor)
    elif turn == 2:
        u_turn(left_motor, right_motor)
    elif turn == 3:
        rotateacw90(left_motor, right_motor)

def collection_detour():
    global grab, box_present, filled_bay
    global need_pick, imminent_next_node
    #print('attempt to collect')
#MAG     global box_polarity, box_row
    junction_node = prev_node            # the junction we came from (2), not the depot (3)
#MAG     box_polarity = read_box_polarity()
    move_forward(left_motor, right_motor, 0.2)
    left_motor.off()
    right_motor.off()
    scan_grab()
#MAG     box_row = choose_bay_row(box_polarity, curr_node)   # curr_node is the depot here
#MAG     set_box_leds(box_polarity)                          # LED on while carrying
    arrive_at_target()                   # stop 2 s at the depot, record it, state -> delivery, pick bay

    grab = True
    box_present = True
    filled_bay = False
    sleep(2)
    move_forward(left_motor, right_motor, 0.8)
    u_turn(left_motor, right_motor)

    if not line_follow_until_return_t():
        halt("Failed to return to depot junction")
        return

    need_pick = False
    imminent_next_node = junction_node
    junction_handling()

def junction_handling():
    global prev_node, curr_node
    global imminent_next_node, target, need_pick

    prev_node = curr_node
    curr_node = imminent_next_node
    if curr_node in DEPOT_NODES:
        left_motor.off()
        right_motor.off()
        sleep(1)
        collection_detour()
        return
    # print(
    #     "\n[NODE] Current:", curr_node,
    #     "| Previous:", prev_node,
    #     "| State:", state
    # )

    if need_pick:
        target = pick_target()
        need_pick = False

    #print("[NAVIGATION] Target:", target)

    if target is None:
        halt("No target available; delivery bays may be full")
        return

    if curr_node == target:
        #print("[NAVIGATION] Target reached")
        arrive_at_target()

    if target is None:
        halt("No target remains")
        return

    following = next_node(board_graph, curr_node, target)

    if following is None:
        halt(
            "No path from " + str(curr_node)
            + " to " + str(target)
        )
        return

    imminent_next_node = following

    # print(
    #     "[NAVIGATION] Planned edge:",
    #     curr_node, "->", imminent_next_node
    # )

    try:
        turn = turn_needed(
            prev_node,
            curr_node,
            imminent_next_node
        )
    except ValueError as error:
        halt(str(error))
        return

    perform_turn(turn)

    # If the planned edge enters the selected delivery bay,
    # perform the delivery detour immediately after turning into it.
    if (
        state == "delivery"
        and target == following
        and following in DELIVERY_BAY_SET
    ):
        return_node = curr_node

        delivery_detour(following, return_node)

        if halted:
            return

        # Reprocess the junction we returned to. This recalculates
        # the next route using the updated state and actual heading.
        junction_handling()
        return

def line_follow_until_return_t():
    """Follow the line until a junction/T pattern is confirmed."""
    global junction_armed, junction_reads, clear_reads
    global box_armed, box_reads, bay_armed

    return_reads = 0
    clear_count = 0
    return_armed = False

    while not halted:
        right_value, left_value, front_value, back_value = (
            get_light_values(
                front_light_sensor,
                back_light_sensor,
                left_light_sensor,
                right_light_sensor
            )
        )

        on_junction = (
            (right_value == 0 and left_value == 1 and front_value == 1)
            or
            (right_value == 1 and left_value == 0 and front_value == 1)
        )
        on_t = right_value == 1 and left_value == 1

        on_return_junction = on_junction or on_t

        # First leave the delivery-bay end pattern before looking
        # for the return junction.
        if not on_return_junction:
            clear_count += 1
            return_reads = 0

            if clear_count >= JUNCTION_CLEAR:
                return_armed = True
        else:
            clear_count = 0

            if return_armed:
                return_reads += 1
            else:
                return_reads = 0

        if return_armed and return_reads >= JUNCTION_CONFIRM:
            left_motor.off()
            right_motor.off()

            # Reset the ordinary detectors so the next line-follow
            # cycle starts with a clean detector state.
            junction_armed = False
            junction_reads = 0
            clear_reads = 0
            box_armed = False
            box_reads = 0
            bay_armed = True

            #print("[DELIVERY] Return junction detected")
            return True

        # Follow the line using the existing sensor behaviour.
        if (
            right_value == 0
            and left_value == 0
            and front_value == 1
        ):
            move_forward(left_motor, right_motor, 0.001)

        elif (
            right_value == 1
            and left_value == 0
            and front_value == 0
        ):
            turn_right(left_motor, right_motor, 0.001)

        elif (
            right_value == 0
            and left_value == 1
            and front_value == 0
        ):
            turn_left(left_motor, right_motor, 0.001)

        elif on_return_junction:
            move_forward(left_motor, right_motor, 0.001)

        else:
            move_forward(left_motor, right_motor, 0.001)

    left_motor.off()
    right_motor.off()
    return False
# ======================================================================
# LINE FOLLOWING AND EVENT DETECTION
# ======================================================================
def delivery_detour(bay_node, return_node):
    global need_pick, imminent_next_node, grab, box_present, filled_bay
    #MAG     global box_polarity, box_row
    scan_drop()
    #MAG     set_box_leds(None)
    #MAG     box_polarity = None
    #MAG     box_row = None
    arrive_at_target()   # 2 s stop, record delivery, state -> to home, target -> 0
    u_turn(left_motor, right_motor)
    if not line_follow_until_return_t():
        halt("Failed to detect return junction")
        return
    grab, box_present, filled_bay = False, False, True
    need_pick = False
    imminent_next_node = return_node

def line_follow():
    global junction_armed, junction_reads, clear_reads
    global box_armed, box_reads, bay_armed

    while not halted:
        right_value, left_value, front_value, back_value = (
            get_light_values(
                front_light_sensor,
                back_light_sensor,
                left_light_sensor,
                right_light_sensor
            )
        )

        on_junction = (
            (right_value == 0 and left_value == 1 and front_value == 1)
            or
            (right_value == 1 and left_value == 0 and front_value == 1)
        )

        on_box = right_value == 1 and left_value == 1

        # Only log unusual sensor patterns to avoid flooding the console.
        #if on_junction or on_box:
            # print(
            #     "[SENSOR EVENT] R:", right_value,
            #     "L:", left_value,
            #     "F:", front_value,
            #     "B:", back_value,
            #     "| Junction:", on_junction,
            #     "| Box:", on_box
            # )

        if on_junction or on_box:
            junction_reads += 1
            clear_reads = 0
        else:
            junction_reads = 0
            clear_reads += 1

        if on_box:
            box_reads += 1
        else:
            box_reads = 0

        if clear_reads >= JUNCTION_CLEAR:
            if not junction_armed or not box_armed:
                pass
                #print("[SENSOR] Junction cleared; rearming detectors")

            junction_armed = True
            box_armed = True

        if front_value == 1:
            bay_armed = True

        # --------------------------------------------------------------
        # Line following
        # --------------------------------------------------------------
        if (
            right_value == 0
            and left_value == 0
            and front_value == 1
        ):
            move_forward(left_motor, right_motor, 0.001)

        elif (
            right_value == 1
            and left_value == 0
            and front_value == 0
        ):
            turn_right(left_motor, right_motor, 0.001)

        elif (
            right_value == 0
            and left_value == 1
            and front_value == 0
        ):
            turn_left(left_motor, right_motor, 0.001)

        elif on_junction:
            if junction_armed and junction_reads >= JUNCTION_CONFIRM:
                junction_armed = False
                box_armed = False

                # print(
                #     "[EVENT] Junction confirmed after",
                #     junction_reads, "reads"
                # )
                return True

            move_forward(left_motor, right_motor, 0.001)

        elif on_box and BOX_RETURNS_EVENT:
            if box_armed and box_reads >= BOX_CONFIRM:
                box_armed = False
                junction_armed = False

                # print(
                #     "[EVENT] Box/T pattern confirmed after",
                #     box_reads, "reads"
                # )
                return True

            move_forward(left_motor, right_motor, 0.001)


        else:
            move_forward(left_motor, right_motor, 0.001)

    return False



amber = Pin(8, Pin.OUT)
amber_timer = Timer()                      # use Timer(-1) on older MicroPython builds

def _flash_amber(timer):
    amber.value(not amber.value())         # keep this tiny: it runs in an interrupt

def start_amber_flash():
    amber_timer.init(period=500, mode=Timer.PERIODIC, callback=_flash_amber)   # 500 ms = 1 Hz

def stop_amber_flash():
    amber_timer.deinit()
    amber.value(0)

#=======================================================================
# Distance code
#+======================================================================
#DIST # ======================================================================
#DIST # DISTANCE-SENSOR CHECKS  (VL53L0X on software I2C: SCL = GP17, SDA = GP22)
#DIST # Enable: Find "#DIST " and Replace with nothing. Keep this block BELOW the
#DIST # original functions, because it replaces them by redefining them:
#DIST #   scan_grab, scan_drop, collection_detour, delivery_detour, next_depot
#DIST # ======================================================================
#DIST try:
#DIST     from machine import SoftI2C
#DIST except ImportError:
#DIST     SoftI2C = None
#DIST #
#DIST DIST_SCL_PIN = 17
#DIST DIST_SDA_PIN = 22
#DIST DIST_DEPOT_MM = 40            # box counts as present at or below this distance (depot)
#DIST DIST_BAY_MM = 40              # bay counts as occupied at or below this distance
#DIST DIST_SAMPLES = 5              # median of this many readings
#DIST USE_MAGNET = False            # set True once every #MAG line is uncommented
#DIST #
#DIST depot_empty = [False, False, False, False]     # one flag per entry in DEPOT_NODES
#DIST _dist_sensor = None
#DIST _dist_failed = False
#DIST #
#DIST def _make_i2c():
#DIST     # GP17 is I2C0's clock but GP22 is I2C1's data, so no hardware bus can use both
#DIST     if SoftI2C is not None:
#DIST         return SoftI2C(scl=Pin(DIST_SCL_PIN), sda=Pin(DIST_SDA_PIN), freq=100000)
#DIST     return I2C(-1, scl=Pin(DIST_SCL_PIN), sda=Pin(DIST_SDA_PIN), freq=100000)
#DIST #
#DIST def get_distance_mm():
#DIST     """One reading in mm (about 8190 = nothing in range), or None if the sensor is unavailable."""
#DIST     global _dist_sensor, _dist_failed
#DIST     if _dist_failed:
#DIST         return None
#DIST     try:
#DIST         if _dist_sensor is None:
#DIST             _dist_sensor = VL53L0X(_make_i2c())
#DIST             _dist_sensor.start()
#DIST         return _dist_sensor.read()
#DIST     except Exception as error:
#DIST         print("[DIST] Sensor error, checks disabled:", error)
#DIST         _dist_failed = True
#DIST         return None
#DIST #
#DIST def box_in_range(label, limit):
#DIST     """True = item within limit mm, False = nothing there, None = sensor unavailable."""
#DIST     readings = []
#DIST     for _ in range(DIST_SAMPLES):
#DIST         d = get_distance_mm()
#DIST         if d is not None:
#DIST             readings.append(d)
#DIST         sleep_ms(10)
#DIST     if not readings:
#DIST         print("[DIST] No valid reading for", label)
#DIST         return None
#DIST     readings.sort()
#DIST     d = readings[len(readings) // 2]
#DIST     print("[DIST]", label, "median:", d, "mm (limit", limit, "mm)")
#DIST     return d <= limit
#DIST #
#DIST def depot_skipped():
#DIST     """Depot had no box: flag it empty and move the depot pointer on. No collection is recorded."""
#DIST     global current_depot
#DIST     i = DEPOT_NODES.index(curr_node)
#DIST     depot_empty[i] = True
#DIST     current_depot = (i + 1) % len(DEPOT_NODES)
#DIST     print("[DEPOT] Empty at node", curr_node, "- flagged empty")
#DIST #
#DIST def bay_marked_full():
#DIST     """Bay already held an item: mark it full so it is never chosen again."""
#DIST     global active_delivery
#DIST     if active_delivery is not None:
#DIST         row, col, node = active_delivery
#DIST         storage[row][col] = 1
#DIST         active_delivery = None
#DIST         print("[DELIVERY] Bay", node, "occupied - marked full")
#DIST #
#DIST def next_depot():
#DIST     """Next depot not flagged empty, starting at current_depot. None if every depot is empty."""
#DIST     global current_depot
#DIST     for k in range(len(DEPOT_NODES)):
#DIST         i = (current_depot + k) % len(DEPOT_NODES)
#DIST         if not depot_empty[i]:
#DIST             current_depot = i
#DIST             print("[TARGET] Next depot:", DEPOT_NODES[i])
#DIST             return DEPOT_NODES[i]
#DIST     print("[TARGET] Every depot is flagged empty")
#DIST     return None
#DIST #
#DIST def scan_grab():
#DIST     """Returns True if a box was grabbed, False if the depot was empty."""
#DIST     global box_polarity
#DIST     arm_down()
#DIST     grab_out60()                                    # arms wide open
#DIST     print('Scanning for box')
#DIST     line_follow_for_ms(SCAN_GRAB_FOLLOW_MS)
#DIST     right_motor.off()
#DIST     left_motor.off()
#DIST     if box_in_range("depot", DIST_DEPOT_MM) is False:   # None (sensor error) carries on and grabs, as before
#DIST         print("[DIST] No box at depot - skipping pickup")
#DIST         return False
#DIST     if USE_MAGNET:
#DIST         box_polarity = read_box_polarity()          # magnet scan only once a box is confirmed
#DIST     print('grab code')
#DIST     sleep(3)
#DIST     arm_up90()
#DIST     grab_out60()
#DIST     right_motor.off()
#DIST     left_motor.off()
#DIST     arm_down()
#DIST     sleep(1)
#DIST     grab_in()
#DIST     sleep(0.5)
#DIST     arm_up30()
#DIST     return True
#DIST #
#DIST def scan_drop():
#DIST     """Returns True if the drop was made, False if the bay already holds an item (nothing dropped)."""
#DIST     print('Scanning for empty space')
#DIST     line_follow_for_ms(SCAN_DROP_FOLLOW_MS)
#DIST     right_motor.off()
#DIST     left_motor.off()
#DIST     if box_in_range("bay", DIST_BAY_MM) is True:       # None (sensor error) carries on and drops, as before
#DIST         print("[DIST] Bay already occupied - aborting drop")
#DIST         return False
#DIST     print('grab code')
#DIST     sleep(1)
#DIST     grab_out30()
#DIST     sleep(0.5)
#DIST     move_back(left_motor, right_motor, 0.8)
#DIST     arm_up90()
#DIST     return True
#DIST #
#DIST def collection_detour():
#DIST     global grab, box_present, filled_bay
#DIST     global need_pick, imminent_next_node, target, box_row
#DIST     print('attempt to collect')
#DIST     junction_node = prev_node                       # the junction we came from
#DIST     move_forward(left_motor, right_motor, 0.2)
#DIST     left_motor.off()
#DIST     right_motor.off()
#DIST     if scan_grab():                                 # box confirmed and picked up
#DIST         if USE_MAGNET:
#DIST             box_row = choose_bay_row(box_polarity, curr_node)   # curr_node is the depot here
#DIST             set_box_leds(box_polarity)
#DIST         arrive_at_target()                          # stop 2 s, record depot, state -> delivery, pick bay
#DIST         grab = True
#DIST         box_present = True
#DIST         filled_bay = False
#DIST         sleep(2)
#DIST         move_forward(left_motor, right_motor, 0.8)
#DIST     else:                                           # empty depot: state and storage untouched
#DIST         arm_up90()
#DIST         grab_out60()
#DIST         depot_skipped()
#DIST         target = pick_target()                      # state is still "to depot" -> next non-empty depot
#DIST     u_turn(left_motor, right_motor)
#DIST     if not line_follow_until_return_t():
#DIST         halt("Failed to return to depot junction")
#DIST         return
#DIST     need_pick = False
#DIST     imminent_next_node = junction_node
#DIST     junction_handling()
#DIST #
#DIST def delivery_detour(bay_node, return_node):
#DIST     global need_pick, imminent_next_node, target
#DIST     global grab, box_present, filled_bay, box_polarity, box_row
#DIST     if scan_drop():                                 # bay was free, box dropped
#DIST         if USE_MAGNET:
#DIST             set_box_leds(None)
#DIST             box_polarity = None
#DIST             box_row = None
#DIST         arrive_at_target()                          # 2 s stop, record delivery, state -> to home, target -> 0
#DIST         u_turn(left_motor, right_motor)
#DIST         if not line_follow_until_return_t():
#DIST             halt("Failed to detect return junction")
#DIST             return
#DIST         grab, box_present, filled_bay = False, False, True
#DIST     else:                                           # bay occupied: abort, still carrying the box
#DIST         bay_marked_full()
#DIST         u_turn(left_motor, right_motor)
#DIST         if not line_follow_until_return_t():
#DIST             halt("Failed to detect return junction")
#DIST             return
#DIST         target = pick_target()                      # state is still "delivery" -> next free bay
#DIST     need_pick = False
#DIST     imminent_next_node = return_node
# ======================================================================
# MAIN
# ======================================================================
def main():
    global halted

    print("[NAVIGATION] Waiting for initial board event")

    button_on = False
    arm_up90()
    grab_out60()
    sleep(2)
    move_forward(left_motor, right_motor, 0.5)
    #grab_in()
    
    while not halted:

        if button.was_clicked():
            button_on = button.is_on()
            if button_on:
                start_amber_flash()
            else:
                stop_amber_flash()
            #print("[BUTTON] State:", "ON" if button_on else "OFF")
            #start_amber_flash()

        if button_on:
            event_detected = line_follow()

            if event_detected:
                junction_handling()
        else:
            left_motor.off()
            right_motor.off()
            sleep_ms(10)

    left_motor.off()
    right_motor.off()
    #print("[NAVIGATION] Stopped")

if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        left_motor.off()
        right_motor.off()
        #print("[ERROR]", error)
        raise
