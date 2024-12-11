from machine import Pin, I2C, ADC
from fifo import Fifo
from ssd1306 import SSD1306_I2C
import micropython
import framebuf
import utime
import time
import network
from time import sleep
from umqtt.simple import MQTTClient
import ujson

micropython.alloc_emergency_exception_buf(200)

SSID = "KME759_Group_2"
PASSWORD = "Ryhma2Koulu."
BROKER_IP = "192.168.2.253"             
port =21883

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

oled_width = 128
oled_height = 64
i2c = I2C(1, scl=Pin(15), sda=Pin(14), freq=400000)
oled_screen = SSD1306_I2C(oled_width, oled_height, i2c)
old_time = 0

adc = ADC(26)

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
            oled_screen.text(f"{item}", 10, i * 10, 1)
        oled_screen.show()

        self.in_submenu = False  # True, kun ollaan alavalikossa
        self.current_row = 0
        self.state = self.cursor

    def cursor(self):
        rot.a.irq(handler=rot.handler, trigger=Pin.IRQ_RISING, hard=True)
        # Tarkistetaan rotary encoder vain, jos ei olla alavalikossa
        if not self.in_submenu:
            while rot.fifo.has_data():
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
        # Tarkista nappulan tila
        rot.a.irq(handler=rot.handler, trigger=Pin.IRQ_RISING, hard=True)
        if button.fifo.has_data():
            value = button.fifo.get()
            if self.in_submenu:
                # Paluu päävalikkoon
                self.in_submenu = False
                self.update_display()
            else:
                # Siirrytään alavalikkoon, jos nappia painetaan
                if value == 2:
                    self.in_submenu = True
                    self.enter_submenu()

    def enter_submenu(self):
        # Aloita valittu alavalikko
        if self.current_row == 0:
            self.HR()
        elif self.current_row == 1:
            self.HRV()
        elif self.current_row == 2:
            self.HISTORY()
        elif self.current_row == 3:
            self.KUBIOS()
    
    
    
    def HR(self):
        rot.a.irq(handler=None, trigger=Pin.IRQ_RISING, hard=True)
        y_prev=oled_height//2
        oled_screen.fill(0)
        y=0
        x=0
        x=0
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
            
            colour=1
            scaled=oled_height-1-((v-sample_min)*oled_height//(sample_max-sample_min))
            scaled=max(0,min(oled_height-1,scaled))
            oled_screen.line(x, y_prev, x+1, scaled , colour)
            y_prev = scaled
            x+=1
            if x >= oled_width:
                x=0
            scaled=oled_height-1-((v-sample_min)*oled_height//(sample_max-sample_min))
            scaled=max(0,min(oled_height-1,scaled))
            oled_screen.line(x, y_prev, x+1, scaled , colour)
            y_prev = scaled
            x+=1
            if x >= oled_width:
                x=0
                oled_screen.fill(0)
            oled_screen.fill_rect(0,0,oled_width,15,0)
            if min_BPM < bpm < max_BPM:
                oled_screen.text(f"BPM: {bpm}", 10, 2, 1)
            else:
                oled_screen.text("Calculating", 10, 2, 1)
            if beat:
                heart = framebuf.FrameBuffer(heart_bitmap,8 , 8, framebuf.MONO_VLSB)
                oled_screen.blit(heart,100,2)
            else:
                heart = framebuf.FrameBuffer(clear_heart_bitmap,8 , 8, framebuf.MONO_VLSB)
                oled_screen.blit(heart,100,2)
            oled_screen.show()
        
            if button.fifo.has_data():
                rot.a.irq(handler=rot.handler, trigger=Pin.IRQ_RISING, hard=True)
                break
        self.update_display()

    def HRV(self):
        rot.a.irq(handler=None, trigger=Pin.IRQ_RISING, hard=True)
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
                     
            if len(ppi_all)< 59:
                oled_screen.fill(0)
                oled_screen.text(f"Collecting data: ",0,0,10)
                oled_screen.text(f"{len(ppi_all)} / 60",0,20,10)
                oled_screen.show()
                
            if len(ppi_all) >=59:
                oled_screen.fill(0)
                average_ppi = calculate_ppi(ppi_all)
                average_bpm = calculate_bpm(ppi_all)
                average_sdnn = calculate_sdnn(ppi_all, average_ppi)
                average_rmssd = calculate_rmssd(ppi_all)
                oled_screen.text(f"HR: {average_bpm}", 0, 10, 10)
                oled_screen.text(f"PPI: {average_ppi}", 0,0,10)
                oled_screen.text(f"SDNN: {average_sdnn}", 0,20 ,10)
                oled_screen.text(f"RMSSD: {average_rmssd}", 0, 30, 10)
                oled_screen.show()
                topic = "hrv"
                measurement = { 
                    "mean_hr": average_bpm, 
                    "mean_ppi": average_ppi, 
                    "rmssd": average_rmssd, 
                    "sdnn": average_sdnn 
                } 
            
   
                def message_callback(topic, msg):
                    print(f"Received message on topic {topic.decode()}: {msg.decode()}")

                try:
                    mqtt_client = connect_mqtt()
                    mqtt_client.set_callback(message_callback)
                    mqtt_client.subscribe(topic)

                    print(f"Subscribed to topic: {topic}")

                    time.sleep(5)

                    msg = ujson.dumps(measurement)
                    mqtt_client.publish(topic, msg)
                    print("Message published:", msg)
                    
                    while True:
                        mqtt_client.wait_msg()
                        break

                except Exception as e:
                    print(f"Failed to send MQTT message: {e}")
                    
                break

            if button.fifo.has_data():
                rot.a.irq(handler=rot.handler, trigger=Pin.IRQ_RISING, hard=True)
                break
            


    def HISTORY(self):
        oled_screen.fill(0)
        test_measurements = ["Measurement 1", "Measurement 2", "Measurement 3", "Measurement 4", "Measurement 5"]
        current_test = 0

        while True:
            # Näytetään testi, johon ollaan siirtymässä
            oled_screen.fill(0)
            for i, test in enumerate(test_measurements):
                pointer = ">" if i == current_test else ""
                oled_screen.text(f"{pointer} {test}", 0, i * 10, 1)
            oled_screen.show()

            # Tarkistetaan nappi ja rotaatio vain HISTORY-valikossa
            if rot.fifo.has_data():
                movement = rot.fifo.get()
                if movement == -1 and current_test < len(test_measurements) - 1:
                    current_test += 1
                elif movement == 1 and current_test > 0:
                    current_test -= 1

            if button.fifo.has_data():
                # Siirrytään valitun testin sisälle nappia painamalla
                value = button.fifo.get()
                if value == 2:
                    self.show_test_detail(current_test)
                break

    def show_test_detail(self, test_index):
        oled_screen.fill(0)
        oled_screen.text(f"Test {test_index + 1}", 10, 10, 1)
        oled_screen.text("Details...", 10, 20, 1)
        oled_screen.show()
        while True:
            if button.fifo.has_data():
                # Palataan takaisin testilistaan nappia painamalla
                break
        
    def KUBIOS(self):
        rot.a.irq(handler=None, trigger=Pin.IRQ_RISING, hard=True)
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
            if button.fifo.has_data():
                rot.a.irq(handler=rot.handler, trigger=Pin.IRQ_RISING, hard=True)
                break
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
                     
            if len(ppi_all)< 59:
                oled_screen.fill(0)
                oled_screen.text(f"Collecting data: ",0,0,10)
                oled_screen.text(f"{len(ppi_all)} / 60",0,20,10)
                oled_screen.show()

            if len(ppi_all)>=59:
                oled_screen.fill(0)
                # Function to connect to WLAN
                try: 
                    mqtt_client=connect_mqtt()
                    mqtt_client.set_callback(message_callback)
                    mqtt_client.subscribe("hr-data") 
                    mqtt_client.subscribe("kubios-response")
                except Exception as e:
                    print("failed connecting kubios", e)
                
                print(ppi_all)
                while True:
                    # Sending a message every 5 seconds.
                    try:
                        topic = "kubios-request"
                        message = {
                            "id": 123,
                            "type":"RRI",
                            "data": ppi_all,
                            "analysis": {"type": "readiness" }
                                }
                        msg = ujson.dumps(message)
                        mqtt_client.publish(topic, msg)
                        sleep(5)
                        mqtt_client.check_msg()
                        time.sleep(2)
                        mqtt_client.check_msg()
                    except Exception as e:
                        print("failed requesting kubios", e)
                        oled_screen.fill(0)
                        oled_screen.text(f"Failed connecting to kubios",0,20,10)
                        oled_screen.text(f"Press to continue",0,40,10)
                        oled_screen.show()
                    if button.fifo.has_data():
                        rot.a.irq(handler=rot.handler, trigger=Pin.IRQ_RISING, hard=True)
                        time.sleep(1)
                        break
                    break
                break

def connect_wlan():
    # Connecting to the group WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    # Attempt to connect once per second
    while wlan.isconnected() == False:
        print("Connecting... ")
        sleep(0.01)

    # Print the IP address of the Pico
    print("Connection successful. Pico IP:", wlan.ifconfig()[0])

    
def connect_mqtt():
    mqtt_client=MQTTClient("", BROKER_IP, port)
    mqtt_client.connect(clean_session=True)
    return mqtt_client

def message_callback(topic, msg):
    try:
        message = ujson.loads(msg)
        oled_screen.fill(0)
        oled_screen.text(f"Mean HR: {message["data"]["analysis"]["mean_hr_bpm"]:.0f}", 0, 0, 30)
        oled_screen.text(f"Mean PPI: {message["data"]["analysis"]["mean_rr_ms"]:.0f}", 0, 10, 30)
        oled_screen.text(f"RMSSD: {message["data"]["analysis"]["rmssd_ms"]:.0f}", 0, 20, 30)
        oled_screen.text(f"SDNN:  {message["data"]["analysis"]["sdnn_ms"]:.0f}", 0, 30, 30)
        oled_screen.text(f"SNS: {message["data"]["analysis"]["sns_index"]:.3f}", 0, 40, 30)
        oled_screen.text(f"PNS: {message["data"]["analysis"]["pns_index"]:.3f}", 0, 50, 30)
        oled_screen.show()
        time.sleep(3)
        oled_screen.fill(0)
        stress = message["data"]["analysis"]["stress_index"]
        oled_screen.text(f"Stress index: {stress:.0f}", 0, 0, 30)
        oled_screen.show()
        if stress < 10:
            oled_screen.text(f":) Low Stress", 0, 30, 30)
            oled_screen.show()
        elif 20 <= stress <=10:
            oled_screen.text(f":/ Moderate Stress", 0, 30, 30)
            oled_screen.show()
        else:
            oled_screen.text(f":/ High Stress", 0, 30, 30)
            oled_screen.show()
    except Exception as e:
        print("failed delivering message", e)


def calculate_ppi(ppi_average):
    if ppi_average:
        average= sum(ppi_average)/len(ppi_average)
        return int(average) 
def calculate_bpm(ppi_average):
    if ppi_average:
        average = sum(ppi_average) // len(ppi_average)
        average = 60000/average
        return int(average)

def calculate_sdnn(average, ppi_average):
    total = 0
    for i in average:
        total += (i-ppi_average)**2
    sdnn = (total / (len(average)-1))**(1/2)
    rounded_sdnn = round(sdnn, 0)
    return int(rounded_sdnn)

def calculate_rmssd(ppi_average):
    i=0
    total=0
    while i < len(ppi_average)-1:
        total += (ppi_average[i+1]-ppi_average[i])**2
        i += 1
    rounded_rmssd = round((total / len(ppi_average)-1)**(1/2),0)
    return int(rounded_rmssd)


oled_screen.fill(0)

try:
    oled_screen.fill(0)
    oled_screen.text("Connecting...", 0, 0, 1)
    oled_screen.show()
    connect_wlan()
    oled_screen.fill(0)
    oled_screen.text("[Connected]", 0, 0, 1)
    oled_screen.show()
    
except Exception as e:
    oled_screen.fill(0)
    oled_screen.text(f"Failed to connect to WLAN: {e}", 0, 0, 1)
    oled_screen.show()
    print(f"Failed to connect to WLAN: {e}")

time.sleep(2)
display = Display()

while True:
    if not display.in_submenu:
        while rot.fifo.has_data():
            display.state()

    while button.fifo.has_data():
        display.row_check()
