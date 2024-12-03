from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
from piotimer import Piotimer
import micropython
import utime

# Constants
MAX_THRESHOLD = 50000
MIN_THRESHOLD = 20000
MIN_HR = 40  # Minimum reasonable BPM
MAX_HR = 190  # Maximum reasonable BPM
WINDOW_SIZE = 5
MAX_HEART_RATE_ENTRIES = 7

# ADC Initialization
adc = ADC(26)
micropython.alloc_emergency_exception_buf(200)

# OLED Initialization
oled_width = 128
oled_height = 64
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_screen = SSD1306_I2C(oled_width, oled_height, i2c)

fifo = Fifo(500, typecode='i')



def timer_handler(timer):
    value = adc.read_u16()
    fifo.put(value)

def alustus():
    count = 0
    values_list = []
    while True:
        adc_value = adc.read_u16()
        utime.sleep_ms(10)
        
        if not MIN_THRESHOLD < adc_value < MAX_THRESHOLD:
            print("noup")
        else:
            values_list.append(adc_value)
            count += 1
            print(adc_value)
        
        if len(values_list) >= 250:
            print("List length reached 250, stopping.")
            break
    
    min_value = min(values_list)
    max_value = max(values_list)
    
    threshold = (max_value + min_value) // 2
    
    print(f"THRESH: {threshold} -- MAX: {max_value}")
    
    return threshold, max_value

def toinen_funktio():
    # Alusta ja käynnistä ajastin
    sample_rate = 100  # 10 ms väli = 100 Hz
    tmr = Piotimer(mode=Piotimer.PERIODIC, freq=sample_rate, callback=timer_handler)
    
    threshold, max_value = alustus()
    # Käytä threshold ja max_value tässä funktiossa
    print(f"Received THRESH: {threshold} and MAX: {max_value}")
    
    current_peak = 0
    previous_peak = 0
    max_sample = max_value
    sample_number = 0
    count = 0
    
    while True:
        adc_value = adc.read_u16()
        if MIN_THRESHOLD < adc_value < MAX_THRESHOLD:
            count += 1
            fifo.put(adc_value)

            if not fifo.empty():
                sample = fifo.get()

                if sample > threshold:
                    if sample > max_sample:
                        max_sample = sample
                        current_peak = count
                        print(f"New max sample: {max_sample} at sample number: {current_peak}")
                else:
                    difference = current_peak - previous_peak
                    print(f"Difference between peaks: {difference}")
                    previous_peak = current_peak

toinen_funktio()
