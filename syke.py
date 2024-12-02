from machine import ADC
import utime

MAX_THRESHOLD = 50000
MIN_THRESHOLD = 20000

adc = ADC(26)

max_peak = 0
reading_count = 0
READING_LIMIT = 100
hearth_rates = []
previous_peak_time = 0
current_peak_time = 0
average=0

window=[]
window_size = 5

def filter(value, window):
    window.append(value)
    if len(window) > window_size:
        window.pop(0)
    return sum(window) // len(window)

while True:
    value = adc.read_u16()
    filtered_value = filter(value, window)
    current_time = utime.ticks_ms()
    if MIN_THRESHOLD < filtered_value < MAX_THRESHOLD:
        if filtered_value > max_peak:
            max_peak = filtered_value
            previous_peak_time = current_peak_time
            current_peak_time = current_time
            if previous_peak_time != 0:
                ppi = utime.ticks_diff(current_peak_time, previous_peak_time)
                hr = int(60/(ppi/1000))      
                
                if 190 >= hr >= 40:
                    hearth_rates.append(hr)
                    if len(hearth_rates) > 7:
                        hearth_rates.pop(0)
                        
                    average = sum(hearth_rates) // len(hearth_rates)
                    print(f"PPI: {ppi} ms	BPM: {average}")

    reading_count += 1
    if reading_count >= READING_LIMIT:
        max_peak = 0
        reading_count = 0
    
    utime.sleep_ms(10)