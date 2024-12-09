from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython
import framebuf
import time
import network
from time import sleep
from umqtt.simple import MQTTClient
import ujson
import utime

micropython.alloc_emergency_exception_buf(200)
adc = ADC(26)
oled_width = 128
oled_height = 64
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_screen = SSD1306_I2C(oled_width, oled_height, i2c)
old_time = 0
heart_bitmap = bytearray([
    0b00011100,
    0b01111111,
    0b11111111,
    0b11111100,
    0b01111111,
    0b01111110,
    0b00011000,
    0b00000000
])

clear_heart_bitmap = bytearray([
    0b00011100,
    0b01100001,
    0b10000011,
    0b10000100,
    0b01000011,
    0b01100001,
    0b00011100,
    0b00000000
])
heart_bitmap = bytearray([
    0b00011100,
    0b01111111,
    0b11111111,
    0b11111100,
    0b01111111,
    0b01111110,
    0b00011000,
    0b00000000
])

clear_heart_bitmap = bytearray([
    0b00011100,
    0b01100001,
    0b10000011,
    0b10000100,
    0b01000011,
    0b01100001,
    0b00011100,
    0b00000000
])

class Calculate:
    def __init__(self):
        self.y_prev=oled_height//2
        self.y=0
        self.x=0
        self.c_250_samples=[7000]
        self.beat=False
        self.bpm=True
        self.interval_ms=0
        self.beats_detected=0
        self.last_bpm=0
        self.last_sample_time=0
        self.sample_time=0
        self.sample_max=50000
        self.sample_min=20000
        self.max_BPM=200
        self.min_BPM=30
        self.ppi_average_calculated=False
        self.v_count=0
        self.last_time=0
        self.max_c_250_samples = 250
        self.moving_ppi_max=10
        self.ppi_average=[]
        self.ppi_all=[]  
     
    def calculate_ppi(self, ppi_average):
        if ppi_average:
            average= sum(ppi_average)/len(ppi_average)
            return int(average) 
    def calculate_bpm(self, ppi_average):
        if ppi_average:
            average = sum(ppi_average) // len(ppi_average)
            average = 60000/average
            return int(average)

    def calculate_sdnn(self, average, ppi_average):
        total = 0
        for i in average:
            total += (i-ppi_average)**2
        sdnn = (total / (len(average)-1))**(1/2)
        rounded_sdnn = round(sdnn, 0)
        return int(rounded_sdnn)

    def calculate_rmssd(self, ppi_average):
        i=0
        total=0
        while i < len(ppi_average)-1:
            total += (ppi_average[i+1]-ppi_average[i])**2
            i += 1
        rounded_rmssd = round((total / len(ppi_average)-1)**(1/2),0)
        return int(rounded_rmssd)

    def hr(self):
        while True:
            new_time= utime.ticks_ms()
            if (new_time - self.last_time) > 4:
                self.last_time = new_time
                v = adc.read_u16()
                if v > self.sample_max or v < self.sample_min:
                    print("no values")
                else:
                    self.c_250_samples.append(v)
                    self.v_count+=1
            
            self.c_250_samples = self.c_250_samples[-self.max_c_250_samples:]
            
            min_value, max_value = min(self.c_250_samples), max(self.c_250_samples)
            
            MAX_THRESHOLD=(min_value+max_value*3)//4
            MIN_THRESHOLD=(min_value+max_value) //2
                
            if v > MAX_THRESHOLD and self.beat == False:
                self.sample_time = new_time
                self.interval_ms = self.sample_time - self.last_sample_time
                if self.interval_ms > 200:
                    self.last_sample_time = self.sample_time
                    if self.ppi_average_calculated:
                        average = self.calculate_ppi(self.ppi_average)
                        if self.interval_ms > (average*0.7) and self.interval_ms <(average*1.3):
                            self.ppi_all.append(self.interval_ms)
                            self.bpm= self.calculate_bpm(self.ppi_all)
                    self.ppi_average.append(self.interval_ms)
                    self.ppi_average = self.ppi_average[-self.moving_ppi_max:]
                    self.beat=True
                
                else:
                    self.beats_detected+=1
                    self.beat=True
                    if self.beats_detected > 5:
                        self.ppi_average_calculated = True
                        self.ppi_average.append(self.interval_ms)
                        self.ppi_average = self.ppi_average[-self.moving_ppi_max:]
                    self.last_sample_time = self.sample_time
            if v < MIN_THRESHOLD and self.beat == True:
                self.beat=False
        
            if self.v_count > 10:
                print(self.bpm)
            
            if len(self.ppi_all) > 59:
                self.average_ppi=self.calculate_ppi(self.ppi_all)
                self.average_bpm= self.calculate_bpm(self.ppi_all)
            
            colour=1
            scaled=oled_height-1-((v-self.sample_min)*oled_height//(self.sample_max-self.sample_min))
            scaled=max(0,min(oled_height-1,scaled))
            oled_screen.line(self.x, self.y_prev, self.x+1, scaled , colour)
            self.y_prev = scaled
            self.x+=1
            if self.x >= oled_width:
                self.x=0
            scaled=oled_height-1-((v-self.sample_min)*oled_height//(self.sample_max-self.sample_min))
            scaled=max(0,min(oled_height-1,scaled))
            oled_screen.line(self.x, self.y_prev, self.x+1, scaled , colour)
            self.y_prev = scaled
            self.x+=1
            if self.x >= oled_width:
                self.x=0
                oled_screen.fill(0)
            oled_screen.fill_rect(0,0,oled_width,15,0)
            if self.min_BPM < self.bpm < self.max_BPM:
                oled_screen.text(f"BPM: {self.bpm}", 10, 2, 1)
            else:
                oled_screen.text("Calculating", 10, 2, 1)
            if self.beat:
                heart = framebuf.FrameBuffer(heart_bitmap,8 , 8, framebuf.MONO_VLSB)
                oled_screen.blit(heart,100,2)
            else:
                heart = framebuf.FrameBuffer(clear_heart_bitmap,8 , 8, framebuf.MONO_VLSB)
                oled_screen.blit(heart,100,2)
            oled_screen.show()

a = Calculate()
a.hr()