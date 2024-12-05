from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython
import utime
import time

adc = ADC(26)
micropython.alloc_emergency_exception_buf(200)

oled_width = 128
oled_height = 64
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_screen = SSD1306_I2C(oled_width, oled_height, i2c)

old_time = 0

# Perus Encoder luokka
class Encoder:
    def __init__(self, rot_a, rot_b):
        self.a = Pin(rot_a, mode=Pin.IN, pull=Pin.PULL_UP)
        self.b = Pin(rot_b, mode=Pin.IN, pull=Pin.PULL_UP)
        self.fifo = Fifo(30, typecode='i')
        self.a.irq(handler=self.handler, trigger=Pin.IRQ_RISING, hard=True)

    def handler(self, pin):
        if self.b.value():
            self.fifo.put(-1)
        else:
            self.fifo.put(1)
        

rot = Encoder(10, 11)

# Nappulan luokka, lisää arvon 2 fifoon jos nappia painetaan.
class Button:
    def __init__(self, button):
        self.button = Pin(button, mode=Pin.IN, pull=Pin.PULL_UP)
        self.button.irq(handler=self.button_handler, trigger=Pin.IRQ_FALLING, hard=True)
        self.fifo = Fifo(30, typecode="i")
        self.old_time = 0

    def button_handler(self, pin):
        delay = 200
        current_time = time.ticks_ms()
        
        if time.ticks_diff(current_time, self.old_time) >= delay:
            self.fifo.put(2)
            self.old_time = current_time

button = Button(12)

class Display:
    def __init__(self):
        oled_screen.fill(0)
        self.menu_items = ["HR", "HRV", "HISTORY", "KUBIOS"]
        for i, item in enumerate(self.menu_items):
            oled_screen.text(f"{item}", 10, i*10, 1)
        oled_screen.show()
        
        self.in_submenu = False
        self.current_row = 0
        self.state = self.cursor
        
    def cursor(self):
        if not rot.fifo.has_data():
            return
        movement = rot.fifo.get()
        if movement == -1 and self.current_row < len(self.menu_items) - 1: 
            self.current_row += 1
        elif movement == 1 and self.current_row > 0:
            self.current_row -= 1
        
        self.update_display()
    
    def update_display(self):
        oled_screen.fill(0)
        
        for i in range(len(self.menu_items)):
            list_item = self.menu_items[i]
            pointer = ">" if i == self.current_row else ""
            oled_screen.text(f"{pointer} {list_item}", 0, i * 10, 1)
        
        oled_screen.show()
        

    def row_check(self):
        if button.fifo.has_data():
            value = button.fifo.get()
            if self.in_submenu:
                self.in_submenu = False
                self.update_display()
            else:
                if value == 2:
                    self.in_submenu = True
                    self.enter_submenu()
    
    def enter_submenu(self):
        if self.current_row == 0:
            self.HR()
        elif self.current_row == 1:
            self.HRV()
        elif self.current_row == 2:
            self.HISTORY()
        elif self.current_row == 3:
            self.KUBIOS()
    
    def HR(self):
        y=0
        c_250_samples=[700]
        beat=False
        bpm=True
        interval_ms=0
        beats_detected=0
        last_bpm=0
        last_sample_time=0
        sample_time=0
        sample_max=50000
        sample_min=20000
        max_BPM=200
        min_BPM=30
        ppi_average_calculated=False
        v_count=0
        last_time=0
        max_c_250_samples = 250
        moving_ppi_max=10
        ppi_average=[]
        ppi_all=[]
        oled_screen.fill(0)
        while True:
            new_time=utime.ticks_ms()
            if (new_time - last_time) > 4:
                last_time = new_time
                v = adc.read_u16()
                if v > sample_max or v < sample_min:
                    print("no values")
                else:
                    c_250_samples.append(v)
                    v_count+=1
            
            c_250_samples = c_250_samples[-max_c_250_samples:]
            
            min_value, max_value = min(c_250_samples), max(c_250_samples)
            
            MAX_THRESHOLD=(min_value+max_value*3)//4
            MIN_THRESHOLD=(min_value+max_value) //2
            
            if v > MAX_THRESHOLD and beat == False:
                sample_time = new_time
                interval_ms = sample_time - last_sample_time
                if interval_ms > 200:
                    if ppi_average_calculated:
                        average = calculate_ppi(ppi_average)
                        if interval_ms > (average*0.7) and interval_ms <(average*1.30):
                            ppi_all.append(interval_ms)
                        beat=True
                        bpm= calculate_bpm(ppi_average)
                        if bpm > max_BPM or bpm < min_BPM:
                            bpm = last_bpm
                        else:
                            last_bpm = bpm
                        
                    ppi_average.append(interval_ms)
                    ppi_average = ppi_average[-moving_ppi_max:]
                    last_sample_time = sample_time
                
                else:
                    beats_detected+=1
                    beat=True
                    if beats_detected > 5:
                        ppi_average_calculated = True
                        ppi_average.append(interval_ms)
                        ppi_average = ppi_average[-moving_ppi_max:]
                    last_sample_time = sample_time
            if v < MIN_THRESHOLD and beat == True:
                beat=False
            
            if v_count > 10:
                print(bpm)
            
            if len(ppi_all) > 59:
                average_ppi=calculate_ppi(ppi_all)
                average_bpm= calculate_bpm(ppi_all)
            
            if button.fifo.has_data():
                break
            
            colour=1
            scaled=(v*oled_height//65535)//2
            oled_screen.pixel(int(y), int(oled_height - scaled), colour)
            oled_screen.show()
            y+=1
            if y >= oled_width:
                y=0
                oled_screen.fill(0)
                oled_screen.text(f"BPM: {bpm}", 10, 10, 1)
            oled_screen.show()
        
        self.update_display()
            

    def HRV(self):
        oled_screen.fill(0)
        oled_screen.text("HRV", 10, 10, 1)
        oled_screen.show()
        
        # Röpö while looppi, ootetaan et jos tulee uus inputti nappulalt nii lopetetaan
        while self.in_submenu:
            if button.fifo.has_data():
                value = button.fifo.get()
                if value == 2:
                    self.in_submenu = False
                    self.update_display()

    def HISTORY(self):
        oled_screen.fill(0)
        oled_screen.text("HISTORY", 10, 10, 1)
        oled_screen.show()
        
        # Röpö while looppi, ootetaan et jos tulee uus inputti nappulalt nii lopetetaan
        while self.in_submenu:
            if button.fifo.has_data():
                value = button.fifo.get()
                if value == 2:
                    self.in_submenu = False
                    self.update_display()

    def KUBIOS(self):
        oled_screen.fill(0)
        oled_screen.text("KUBIOS", 10, 10, 1)
        oled_screen.show()
        
        # Röpö while looppi, ootetaan et jos tulee uus inputti nappulalt nii lopetetaan
        while self.in_submenu:
            if button.fifo.has_data():
                value = button.fifo.get()
                if value == 2:
                    self.in_submenu = False
                    self.update_display()

def calculate_ppi(ppi_average):
    if ppi_average:
        average= sum(ppi_average)/len(ppi_average)
        return int(average) 
def calculate_bpm(ppi_average):
    if ppi_average:
        average = sum(ppi_average) // len(ppi_average)
        average = 60000/average
        return int(average)


display = Display()


while True: 
    
    while rot.fifo.has_data():
        display.state()
    
    while button.fifo.has_data():
        display.row_check()