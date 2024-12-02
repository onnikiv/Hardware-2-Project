from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython
import utime
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
            scaled = round(adc_value * oled_height // 65535)

            oled_screen.pixel(int(y), int(oled_height - scaled), colour)
            oled_screen.show()
            y += 1
            if y >= oled_width:
                y = 0
                oled_screen.fill(0)



MAX_THRESHOLD = 50000
MIN_THRESHOLD = 20000

fifo = Fifo(500, typecode='i')

def read_sample():
    utime.sleep_ms(10)
    return adc.read_u16()
        
    



def keep_reading():
    ALL_VALUES = []
    y = 0
    colour = 1
    oled_screen.fill(0)
    max_value = 0
    current_peak = 0
    sample_number = 0

    while True:
        sample = read_sample()
        current_time = utime.ticks_ms()
        
        if MIN_THRESHOLD < sample < MAX_THRESHOLD:
            fifo.put(sample)
            value = fifo.get()
            ALL_VALUES.append(value)
            scaled_adc_value = (sample * oled_height // 65535)
            
            if len(ALL_VALUES) >= 200:

                threshold = (min(ALL_VALUES) + max(ALL_VALUES)) // 2
                
                ALL_VALUES = []

                print(threshold)
                
            if sample > max_value:
                max_value = sample
                current_peak = sample_number
                print(current_peak)
            

            oled_screen.pixel(int(y), int(oled_height - scaled_adc_value), colour)
            oled_screen.show()
            y += 1
            if y >= oled_width:
                y = 0
                oled_screen.fill(0)

keep_reading()



"""
if len(values) >= 50: # Jos listan pituus ylittää 100 niin mennään takasin alkuun
                min_value = min(values)
                max_value = max(values)
                max_index = values.index(max_value)
                max_time = times[max_index]
                max_time_since_start = utime.ticks_diff(max_time, start_time)
                
                print(f"Min: {min_value}, Max: {max_value}")
                print(f"Time of max value: {max_time_since_start} ms")
                
                if first_peak_time is None:
                    first_peak_time = max_time
                else:
                    next_peak_time = max_time
                    interval = next_peak_time - first_peak_time
                    print(f"Interval between peaks: {interval} ms")
                    first_peak_time = next_peak_time  # Update first_peak_time for the next interval calculation
                
                values = []
                times = []
                threshold = (min_value + max_value) // 2
                print(f"Threshold: {threshold}")
"""