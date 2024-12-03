from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
from piotimer import Piotimer
import micropython
import utime
import time


micropython.alloc_emergency_exception_buf(200)

MAX_THRESHOLD = 50000
MIN_THRESHOLD = 20000

sample_rate = 100  # 250 Hz näytteenottotaajuus




class isr_adc:
    def __init__(self, adc_pin_nr):
        self.av = ADC(adc_pin_nr)  # Alustaa ADC:n tietylle pinnille
        self.samples = Fifo(50)  # FIFO-puskuri, johon arvot tallennetaan
        self.dbg = Pin(0, Pin.OUT)  # Debug-pinni

    def handler(self, tid):

        adc_value = self.av.read_u16()  # Lukee ADC-arvon
        
        # Tallenna ADC-arvo ja siihen kulunut aika FIFO-puskurille
        self.samples.put(self.av.read_u16())
    
        # Debug-pinni
        self.dbg.toggle()
        
# Luodaan isr_adc-instanssi
ia = isr_adc(26)

# Aikavälin ajastin
tmr = Piotimer(period=10, mode=Piotimer.PERIODIC, callback=ia.handler)


max_peak = 0
reading_count = 0
READING_LIMIT = 100
hearth_rates = []
previous_peak_index = 0
current_peak_index = 0
average = 0

# Pääsilmukka
while True:

    if not ia.samples.empty():
        value = ia.samples.get()
        
        if MIN_THRESHOLD < value < MAX_THRESHOLD:
            if value > max_peak:
                max_peak = value
                previous_peak_index = current_peak_index
                current_peak_index = reading_count
                if previous_peak_index != 0:
                    ppi = (current_peak_index - previous_peak_index)  * 10# 10 ms väli
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