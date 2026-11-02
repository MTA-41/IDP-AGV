from machine import Pin, PWM, I2C, ADC, Timer
from time import sleep





def get_light_values(left_sensor, front_sensor):
    return [
        
        left_sensor.value(),
        front_sensor.value()

    ]


left_light_sensor = Pin(20, Pin.IN)
front_light_sensor = Pin(19, Pin.IN)
left_value, front_value = get_light_values(left_light_sensor, front_light_sensor)
#front_value = get_light_values(front_light_sensor)


while True:
    print('hi')
    left_value, front_value = get_light_values(left_light_sensor, front_light_sensor)
    print(f'{left_value}')
    sleep(0.2)
    print(f'front {front_value}')