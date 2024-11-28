from machine import ADC
import utime

MAX_THRESHOLD = 50000
MIN_THRESHOLD = 20000

adc = ADC(26)

max_peak = 0
reading_count = 0
READING_LIMIT = 100

previous_peak_time = 0
current_peak_time = 0

while True:
    value = adc.read_u16()
    current_time = utime.ticks_ms()
    
    if MIN_THRESHOLD < value < MAX_THRESHOLD:
        if value > max_peak:
            max_peak = value
            previous_peak_time = current_peak_time
            current_peak_time = current_time
            if previous_peak_time != 0:
                ppi = utime.ticks_diff(current_peak_time, previous_peak_time)
                if ppi > 100:
                    print(f"PPI: {ppi} ms	BPM: {int(60/(ppi/1000))}")
    
    reading_count += 1
    if reading_count >= READING_LIMIT:
        max_peak = 0
        reading_count = 0
    
    utime.sleep_ms(10)
