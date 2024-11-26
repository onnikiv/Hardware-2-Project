from machine import Pin, I2C
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import time


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


    def button_handler(self, pin):
        delay = 200
        current_time = time.ticks_ms()
        
        if time.ticks_diff(current_time, old_time) >= delay:
            self.fifo.put(2)
            old_time = current_time

button = Button(12)


class Display:
    
    def __init__(self):
        oled_screen.fill(0)
        self.menu_items = [" HR", " HRV", " HISTORY", " KUBIOS"]
        
        for i, item in enumerate(self.menu_items):
            print(f"Item {i}: {item}") # DEBUG
            oled_screen.text(item, 0, i*10, 1)

        oled_screen.show()
        
        self.current_row = 0
        self.state = self.cursor
        
        
    def cursor(self):
        if not rot.fifo.has_data():
            return
        movement = rot.fifo.get()
        print(movement) # DEBUG
        if movement == -1 and self.current_row < 4: 
            self.current_row += 1
        elif movement == 1 and self.current_row > 0:
            self.current_row -= 1
        
        self.update_display()
    
    def update_display(self):
        oled_screen.fill(0)
        
        for i in range(len(self.menu_items)):
            list_item = self.menu_items[i]
            pointer = ">" if i == self.current_row else ""
            oled_screen.text(f"{pointer}{list_item}", 0, i * 10, 1)

    
        
        oled_screen.show()
        
display = Display()



while True:
    while rot.fifo.has_data():
        display.state()