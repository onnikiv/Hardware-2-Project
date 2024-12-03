from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
from piotimer import Piotimer
import micropython
import utime
import time


micropython.alloc_emergency_exception_buf(200)

oled_width = 128
oled_height = 64
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_screen = SSD1306_I2C(oled_width, oled_height, i2c)



sample_rate = 100 # 10ms välein lisätään arvo fifoon

class isr_adc:
    def __init__(self, adc_pin_nr):
        self.av = ADC(adc_pin_nr)
        self.samples = Fifo(50)
        self.dbg = Pin(0, Pin.OUT)

    def handler(self, tid):
        adc_value = self.av.read_u16()
        
        self.samples.put(self.av.read_u16())
        # Debug-pinni
        self.dbg.toggle()


ia = isr_adc(26)
tmr = Piotimer(mode=Piotimer.PERIODIC, freq=sample_rate, callback=ia.handler)

MAX_THRESHOLD = 50000
MIN_THRESHOLD = 20000
max_peak = 0
reading_count = 0
READING_LIMIT = 100
hearth_rates = []
previous_peak_index = 0
current_peak_index = 0
average = 0

while True:
    if not ia.samples.empty():
        value = ia.samples.get()
        
        if MIN_THRESHOLD < value < MAX_THRESHOLD:
            if value > max_peak:
                max_peak = value
                previous_peak_index = current_peak_index
                current_peak_index = reading_count
                if previous_peak_index != 0:
                    ppi = (current_peak_index - previous_peak_index)  * 10
                    hr = int(60 / (ppi / 1000))

                    if 30 <= hr <= 200:
                        hearth_rates.append(hr)
                        if len(hearth_rates) > 5:
                            hearth_rates.pop(0)

                        average = sum(hearth_rates) // len(hearth_rates)
                        print(f"PPI: {ppi} ms\tBPM: {average}")

        reading_count += 1
        if reading_count >= READING_LIMIT:
            max_peak = 0
            reading_count = 0
    