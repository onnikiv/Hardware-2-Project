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
            print("2 laitettu fifoon")
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
        colour = 1
        oled_screen.fill(0)
        while self.in_submenu:
            if button.fifo.has_data():
                value = button.fifo.get()
                if value == 2:
                    self.in_submenu = False
                    self.update_display()
                    
            adc_value = adc.read_u16()
            scaled = (adc_value * oled_height // 65535)
            print(scaled)
            oled_screen.pixel(int(y), int(oled_height - scaled), colour)
            oled_screen.show()
            y += 1
            if y >= oled_width:
                y = 0
                oled_screen.fill(0)
    

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

display = Display()


while True: 
    
    while rot.fifo.has_data():
        display.state()
    
    while button.fifo.has_data():
        display.row_check()