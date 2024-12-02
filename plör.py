from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython
import time
adc = ADC(26)
micropython.alloc_emergency_exception_buf(200)

oled_width = 128
oled_height = 64
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_screen = SSD1306_I2C(oled_width, oled_height, i2c)

old_time = 0


def HR():
    y=0
    colour = 1
    oled_screen.fill(0)
    while True:
        adc_value = adc.read_u16()
        
        if 20000 < adc_value < 50000:
            scaled = (adc_value * oled_height // 65535)

            oled_screen.pixel(int(y), int(oled_height - scaled), colour)
            oled_screen.show()
            y += 1
            if y >= oled_width:
                y = 0
                oled_screen.fill(0)


import utime

class Syke:
    def __init__(self):
        self.MIN_THRESHOLD = 20000
        self.MAX_THRESHOLD = 50000
        self.peaks = []
        self.peak_times = []

    def get_adc(self):
        return adc.read_u16()
    
    def read_adc(self):
        max_peak = 0

        while True:
            adc_value = self.get_adc()
            current_time = utime.ticks_ms()
            print(current_time)
            utime.sleep_ms(10)
            


    def execute(self):
        self.read_adc()

syke = Syke()

while True:
    syke.execute()