import random, re
import tkinter as tk

import serial
import smbus
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
import pygame

from time import sleep
from datetime import datetime


class Temperature(object):
    def __init__(self):
        self._temperature_value = 0
        self._observers = []

    def get_temperature(self):
        return self._temperature_value

    def set_temperature(self, temperature):
        self._temperature_value = temperature
        for callback in self._observers:
            callback(self._temperature_value)

    def bind_to(self, callback):
        self._observers.append(callback)


class Time(object):
    def __init__(self):
        self._seconds = 0
        self._minutes = 0
        self._hours = 0
        self._observers = []

    def set_time(self, seconds, minutes, hours):
        self._seconds = seconds
        self._minutes = minutes
        self._hours = hours
        self._exec_callbacks()

    def difference(self, other_time):
        fmt = '%H:%M:%S'
        time_one = '{:0>2}:{:0>2}:{:0>2}'.format(self._hours, self._minutes, self._seconds)
        time_two = '{:0>2}:{:0>2}:{:0>2}'.format(other_time._hours, other_time._minutes, other_time._seconds)
        tdelta = datetime.strptime(time_one, fmt) - datetime.strptime(time_two, fmt)
        
        seconds = tdelta.seconds
        
        hours = seconds // (60*60)
        seconds %= (60*60)
        minutes = seconds // 60
        seconds %= 60
        
        return (seconds, minutes, hours)

    def _exec_callbacks(self):
        for callback in self._observers:
            callback(self._seconds, self._minutes, self._hours)

    def bind_to(self, callback):
        self._observers.append(callback)


class TemperatureFrame(tk.Frame):
    def __init__(self, temperature, label=None, master=None, flash=False):
        super().__init__(master)
        if label is None:
            self.label = 'Unknown'
        else:
            self.label = label
        self.flash = flash
        self.alert_temp = 0
        self._create_text()
        temperature.bind_to(self._update_temperature)

    def set_alert_temp(self, alert_temp):
        self.alert_temp = alert_temp

    def _create_text(self):
        self.temperature_label = tk.Label(self.master, text=u'{}: 0\u2109'.format(self.label), font=('Arial', 20))
        self.temperature_label.pack()

    def _update_temperature(self, temperature):
        self.temperature_label['text'] = u'{}: {}\u2109'.format(self.label, round(temperature, 2))

        if temperature >= self.alert_temp and self.flash:
            self.temperature_label['fg'] = 'red'
        else:
            self.temperature_label['fg'] = 'black'


class ThermometerFrame(tk.Frame):
    def __init__(self, temperature, label, master=None):
        super().__init__(master)
        self.canvas = tk.Canvas(self, width=300, height=800)
        self.canvas.pack()

        self.photo = tk.PhotoImage(file="thermometer.gif")
        self.canvas.create_image(200, 300, image=self.photo)
        self.canvas.create_oval(200 - 42, 530 - 42, 200 + 42, 530 + 42 , fill='red')
        self.canvas.create_text(200, 580, text=label, font=('Arial', 12))
        temperature.bind_to(self.draw_mercury)
    
    def draw_mercury(self, temperature):
        self.canvas.delete('line')
        draw_height = 530 - temperature * 4
        if draw_height <= 80:
            draw_height = 80
        self.canvas.create_line(200, 530, 200, draw_height, width=35, fill='red', tag='line') 


class TimeFrame(tk.Frame):
    def __init__(self, time, label=None, master=None, toggeling=False,):
        super().__init__(master)
        self.label = label
        self._create_text()
        time.bind_to(self._update_time)

        if toggeling:
            self._create_toggle_canvas()

    def toggle_hours(self):
        self.toggle_canvas.delete('min')
        self.toggle_canvas.delete('sec')
        self.toggle_canvas.create_line(235, 0, 265, 0, width=5, tags='hour')

    def toggle_minutes(self):
        self.toggle_canvas.delete('hour')
        self.toggle_canvas.delete('sec')
        self.toggle_canvas.create_line(280, 0, 310, 0, width=5, tags='min')

    def toggle_seconds(self):
        self.toggle_canvas.delete('hour')
        self.toggle_canvas.delete('min')
        self.toggle_canvas.create_line(325, 0, 355, 0, width=5, tags='sec')  

    def _create_text(self):
        self.time_label = tk.Label(self.master, text='{}: 00:00:00'.format(self.label), font=('Arial', 20))
        self.time_label.pack()

    def _create_toggle_canvas(self):
        self.toggle_canvas = tk.Canvas(self, width=600, height=10)
        self.toggle_canvas.pack()

    def _update_time(self, seconds, minutes, hours):
        self.time_label['text'] = '{}: {:0>2}:{:0>2}:{:0>2}'.format(self.label, hours, minutes, seconds)


class OptionsFrame(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        
        self.alert_temp = 85
        self.tk_alert_temp = tk.StringVar()
        self.tk_alert_temp.set('85')

        self.baud_rate = tk.StringVar()
        self.baud_rate.set('9600')

        self.num_bits = tk.StringVar()
        self.num_bits.set('8')

        self.parity = tk.StringVar()
        self.parity.set('NONE')

        self.stop_bits = tk.StringVar()
        self.stop_bits.set('1')
        
        self._create_widgets()

    def _create_widgets(self):
        alert_temp_label = tk.Label(self, text='Alert Temp')
        alert_temp_label.grid(row=0)
        
        self.alert_temp_entry = tk.Entry(self, textvariable=self.tk_alert_temp)
        self.alert_temp_entry.grid(row=0, column=1)

        set_temp = tk.Button(self, text='Set', command=self.set_alert_temp)
        set_temp.grid(row=0, column=2)

        baud_rate_label = tk.Label(self, text='Baud Rate')
        baud_rate_label.grid(row=1)

        self.baud_rate_entry = tk.OptionMenu(self, self.baud_rate, '9600', '19200', '38400', '57600')
        self.baud_rate_entry.grid(row=1, column=1)

        num_bits_label = tk.Label(self, text='Number of Bits')
        num_bits_label.grid(row=1, column=2)

        self.num_bits_entry = tk.OptionMenu(self, self.num_bits, '7', '8')
        self.num_bits_entry.grid(row=1, column=3)

        parity_label = tk.Label(self, text='Parity')
        parity_label.grid(row=2)

        self.parity_menu = tk.OptionMenu(self, self.parity, 'NONE', 'EVEN', 'ODD')
        self.parity_menu.grid(row=2, column=1)

        stop_bits_label = tk.Label(self, text='Number of Stop Bits')
        stop_bits_label.grid(row=2, column=2)

        self.stop_bits_entry = tk.OptionMenu(self, self.stop_bits, '1', '2')
        self.stop_bits_entry.grid(row=2, column=3)

        self.reconfigure = tk.Button(self, text='Reconfigure', command=self.reconfigure_serial)
        self.reconfigure.grid(row=3)

    def _create_packet(self):
        payload = 'B{},N{},P{},S{}$'.format(self.baud_rate.get(), self.num_bits.get(), self.get_coded_parity(), self.stop_bits.get())
        return payload

    def reconfigure_serial(self):
        #print(self._create_packets())
        packet = self._create_packet()
        print(packet)
        ser.write(bytes(packet, 'utf-8'))

        sleep(1)
        ser.baudrate = int(self.baud_rate.get())
        ser.bytesize = self.get_pyserial_bytesize()
        ser.parity = self.get_pyserial_parity()
        ser.stopbits = self.get_pyserial_stopbits()
        ser.flushInput()
        ser.flushOutput()

    def get_pyserial_bytesize(self):
        if int(self.num_bits.get()) == 5:
            return serial.FIVEBITS
        elif int(self.num_bits.get()) == 6:
            return serial.SIXBITS
        elif int(self.num_bits.get()) == 7:
            return serial.SEVENBITS
        elif int(self.num_bits.get()) == 8:
            return serial.EIGHTBITS

    def get_pyserial_parity(self):
        if self.parity.get() == 'EVEN':
            return serial.PARITY_EVEN
        elif self.parity.get() == 'NONE':
            return serial.PARITY_NONE
        return serial.PARITY_ODD

    def get_pyserial_stopbits(self):
        if int(self.stop_bits.get()) == 1:
            return serial.STOPBITS_ONE
        elif int(self.stop_bits.get()) == 2:
            return serial.STOPBITS_TWO
            
    
    def get_coded_parity(self):
        if self.parity.get() == 'EVEN':
            return 1
        elif self.parity.get() == 'NONE':
            return 2
        return 0

    def set_alert_temp(self):
        if self.tk_alert_temp.get() == '':
            self.alert_temp = 0
        else:
            self.alert_temp = int(self.tk_alert_temp.get())

    def get_alert_temp(self):
        return self.alert_temp


class Application(tk.Frame):
    def __init__(self, ren_temperature, rtc_temperature, time, overheat_time, normal_time, time_overheated, master=None):
        super().__init__(master)
        self.pack()
        self.init_frames(ren_temperature, rtc_temperature, time, overheat_time, normal_time, time_overheated)

    def init_frames(self, ren_temperature, rtc_temperature, time, overheat_time, normal_time, time_overheated):
        
        self.themometer_frame = ThermometerFrame(ren_temperature, 'Renesas', self)
        self.themometer_frame.pack(side=tk.LEFT)
        
        self.rtc_themometer_frame = ThermometerFrame(rtc_temperature, 'RTC', self)
        self.rtc_themometer_frame.pack(side=tk.LEFT)
        
        self.ren_temperature_frame = TemperatureFrame(ren_temperature, 'Renesas', self, flash=True)
        self.ren_temperature_frame.pack()

        self.rtc_temperature_frame = TemperatureFrame(rtc_temperature, 'RTC', self)
        self.rtc_temperature_frame.pack()

        self.time_frame = TimeFrame(time, 'Clock', self, toggeling=True)
        self.time_frame.pack()

        self.overheat_time_frame = TimeFrame(overheat_time, 'Last Time Overheat', self)
        self.overheat_time_frame.pack()

        self.last_normal_time_frame = TimeFrame(normal_time, 'Last Time Normal', self)
        self.last_normal_time_frame.pack()

        self.time_overheated_frame = TimeFrame(time_overheated, 'Time Overheated', self)
        self.time_overheated_frame.pack()

        


        self.options_frame = OptionsFrame(self)
        self.options_frame.pack()


def int_to_bcd(x):
    """
    This translates an integer into binary coded decimal >>> int_to_bcd(4) 4
    >>> int_to_bcd(34)
    22
    """

    if x < 0:
        raise ValueError("Cannot be a negative integer")

    bcdstring = ''
    while x > 0:
        nibble = x % 16
        bcdstring = str(nibble) + bcdstring
        x >>= 4
        
    if bcdstring == '':
        bcdstring = 0
    return int(bcdstring)


HOURS = 'HOUR'
MINUTES = 'MINUTE'
SECONDS = 'SECONDS'
address = 0x68
bus = smbus.SMBus(1)
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)

MAX_ADC = 1023
SPI_PORT   = 0
SPI_DEVICE = 0
mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
    

def decrement_unit_time(curr_selected_option, time, bus):
    """
    Decrements the unit of time on the real time clock
    based on the current selection in the GUI
    """
    if curr_selected_option == HOURS:
        hours = int_to_bcd(bus.read_byte_data(address, 2))
        bus.write_byte_data(address, 2, hours - 1)
    elif curr_selected_option == MINUTES:
        minutes = int_to_bcd(bus.read_byte_data(address, 1))
        bus.write_byte_data(address, 1, minutes - 1)
    elif curr_selected_option == SECONDS:
        seconds = int_to_bcd(bus.read_byte_data(address, 0))
        bus.write_byte_data(address, 0, seconds - 1)

def increment_unit_time(curr_selected_option, time, bus):
    """
    Increments the unit of time on the real time clock
    based on the current selection in the GUI
    """
    if curr_selected_option == HOURS:
        hours = int_to_bcd(bus.read_byte_data(address, 2))
        bus.write_byte_data(address, 2, hours + 1)
    elif curr_selected_option == MINUTES:
        minutes = int_to_bcd(bus.read_byte_data(address, 1))
        bus.write_byte_data(address, 1, minutes + 1)
    elif curr_selected_option == SECONDS:
        seconds = int_to_bcd(bus.read_byte_data(address, 0))
        bus.write_byte_data(address, 0, seconds + 1)

if __name__ == '__main__':

    root = tk.Tk()
    root.wm_title('Temperature Display')
    root.geometry('1100x700')
    
    pygame.mixer.init()
    pygame.mixer.music.load('blip.mp3')
     
    bus.write_byte_data(address, 0, 0)
    bus.write_byte_data(address, 1, 0)
    bus.write_byte_data(address, 2, 0)
    bus.write_byte_data(address, 3, 0)
    
    ren_temperature = Temperature()
    rtc_temperature = Temperature()
    
    time  = Time()
    normal_time = Time()
    overheat_time = Time()
    time_overheated = Time()

    overheat_flag = False
    curr_selected_option = None

    temp = 0
    alert_temp = 85
    
    app = Application(ren_temperature, rtc_temperature, time, overheat_time, normal_time, time_overheated, master=root)

    ser.flushInput()
    ser.flushOutput()
    
    while True:
        data = ''
        if app.options_frame.get_alert_temp() != alert_temp:
            ser.write(bytes('T{}$'.format(app.options_frame.get_alert_temp()), 'utf-8'))
            
        alert_temp = app.options_frame.get_alert_temp()
        
        app.ren_temperature_frame.set_alert_temp(alert_temp)

        # Read in the time from the real time clock
        # they are read in BCD, they need to be converted. 
        seconds = int_to_bcd(bus.read_byte_data(address, 0))
        minutes = int_to_bcd(bus.read_byte_data(address, 1))
        hours = int_to_bcd(bus.read_byte_data(address, 2))
        day = int_to_bcd(bus.read_byte_data(address, 3))

        # Set the time on the GUI
        time.set_time(seconds, minutes, hours)

        # Read the temperature from the Real Time Clock Register
        rtc_temp = bus.read_byte_data(address, 17)
        
        #if ser.inWaiting() > 0:
         #   try:
        #       data = str(ser.readline(ser.inWaiting()), 'utf-8')
         #   except BlockingIOError:
          #      pass

        data = str(ser.readline(), 'utf-8')

        if re.match(r'ACTION:CBUT', data):
            increment_unit_time(curr_selected_option, time, bus)
            
        elif re.match(r'ACTION:RBUT', data):
            decrement_unit_time(curr_selected_option, time, bus)
            
        elif re.match(r'ACTION:LBUT', data):
            if curr_selected_option == HOURS:
                app.time_frame.toggle_minutes()
                curr_selected_option = MINUTES
            elif curr_selected_option == MINUTES:
                app.time_frame.toggle_seconds()
                curr_selected_option = SECONDS
            elif curr_selected_option == SECONDS or curr_selected_option is None:
                app.time_frame.toggle_hours()
                curr_selected_option = HOURS
        elif re.match(r'TEMP:[0-9.]*', data):
            temp = float(re.findall(r'TEMP:([0-9.]*)', data)[0])
            ren_temperature.set_temperature(temp)       
        
        rtc_temperature.set_temperature(rtc_temp * 1.8 + 32)

        # If the temperature is above the alert temp
        # Then set the overheat time
        if temp > alert_temp and not overheat_flag:
            overheat_time.set_time(seconds, minutes, hours)
            overheat_flag = True

        # If it was overheating and goes back to normal
        # set the last normal time clock, and display the time
        # that it was overheated
        if temp < alert_temp and overheat_flag:
            normal_time.set_time(seconds, minutes, hours)
            time_diff = normal_time.difference(overheat_time)
            time_overheated.set_time(time_diff[0], time_diff[1], time_diff[2])
            overheat_flag = False
        
        root.update_idletasks()
        root.update()

        adc_value = mcp.read_adc(0)
        
        pygame.mixer.music.set_volume(adc_value/MAX_ADC)
        if(ren_temperature.get_temperature() >= alert_temp):
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() == True:
                continue
