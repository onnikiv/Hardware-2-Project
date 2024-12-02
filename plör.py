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

        

def read_sample():
    utime.sleep_ms(10)
    return adc.read_u16()
        
    



def keep_reading():
    values = []
    times = []
    start_time = utime.ticks_ms()  # ekaa kertaa otetaan aika
    first_peak_time = next_peak_time = None #Alustetaan tulevat huiput
    
    y=0
    colour = 1
    oled_screen.fill(0)
    
    while True:
        
        sample = read_sample()
        current_time = utime.ticks_ms() # uusi nykyinen aika katsotaan
        
        
        if MIN_THRESHOLD < sample < MAX_THRESHOLD: # Jos arvot on siellä 30 tuhannessa niin dibdib
            time_since_start = utime.ticks_diff(current_time, start_time) #ticks diffil katotaan kuinka paljon aikaa on alusta verratuna kuinka kauan looppi on pyörinyt
            # DEBUG print(f"Time since start: {time_since_start} ms")
            
            scaled_adc_value = (sample * oled_height // 65535)
            values.append(scaled_adc_value)
            times.append(current_time)
            
    # Täs kohtaa piirretään näyttöön skaalatut arvot
            oled_screen.pixel(int(y), int(oled_height - scaled_adc_value), colour)
            oled_screen.show()
            y += 1
            if y >= oled_width:
                y = 0
                oled_screen.fill(0) #Päivitetään jos y akselilla ylitetään OLED:in maximi
            
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

keep_reading()