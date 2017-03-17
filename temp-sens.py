import os
import glob
import time
import RPi.GPIO as gpio
import sys
import json
import sensor
import MySQLdb as mysql

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

BOARD_MODE = gpio.BOARD
PIN_HEAT = 13 
PIN_RED_LED = 15
PIN_GREEN_LED = 11

base_dir='/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder+ '/w1_slave'

SETTINGS_FILE = 'settings.json'
STATUS_FILE = '/var/www/html/status.json'
SYSTEM_STATUS = None
SETTINGS = None


def setup_GPIO():

    print "Setting up GPIO"
    gpio.setwarnings(False)

    # Set board mode
    gpio.setmode(BOARD_MODE)

    # Setup output pins
    gpio.setup(PIN_HEAT, gpio.OUT)
    gpio.setup(PIN_RED_LED, gpio.OUT)
    gpio.setup(PIN_GREEN_LED, gpio.OUT)
    

def read_settings():
    s = None
    with open(SETTINGS_FILE, 'r') as file:
        s = file.read();
    data = json.loads(s)
    return data


def write_settings(s):
    with open(SETTINGS_FILE, 'w') as outfile:
        json.dump(s, outfile)

        
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines


def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:]!='YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string)/1000
        temp_f = temp_c * 9/5+32
        return temp_c

    
def compare_temp(temp):
    target = float(SETTINGS['current_target'])
    return (target < float(temp))
    

def is_override():
    override_status = SETTINGS['override']
    if override_status:
        override_temp = SETTINGS['override_temp']
        override_duration = SETTINGS['override_duration']
        override_start = read_time()

    else:
        return False

    
def read_time():
    return time.strftime("%H:%M:%S")


def read_hour():
    return time.strftime("%H")


def toggle_target():
    global SETTINGS
    cur_hr = read_hour()
    if 7 <= float(cur_hr) < 9:
        if SETTINGS['current_target'] != SETTINGS['target_high_temp']:
            SETTINGS['current_target'] = SETTINGS['target_high_temp']
    elif 15 <= float(cur_hr) < 21:
        if SETTINGS['current_target'] != SETTINGS['target_high_temp']:
            SETTINGS['current_target'] = SETTINGS['target_high_temp']
    else:
        if SETTINGS['current_target'] != SETTINGS['target_low_temp']:
            SETTINGS['current_target'] = SETTINGS['target_low_temp']
    write_settings(SETTINGS)

    
def turn_on():
    global SYSTEM_STATUS
    SYSTEM_STATUS = "on"
    gpio.output(11, gpio.HIGH)
    gpio.output(13, gpio.HIGH)
    gpio.output(15, gpio.LOW)

    
def turn_off():
    global SYSTEM_STATUS
    SYSTEM_STATUS = "off"
    gpio.output(11, gpio.LOW)
    gpio.output(13, gpio.LOW)
    gpio.output(15, gpio.HIGH)

def log_temp():
    db = mysql.connect(host="XXX.XXX.XXX.XXX", user="XXXXXX", passwd="XXXXXX", db="XXXXXX")

    cursor = db.cursor()

    current_temp = sensor.readtemperature()
    sql = "insert into sensors VALUES(null, 'living room', {}, null)".format(current_temp)
    rows = cursor.execute(sql)
    
    db.commit()
    db.close()
    
    
    
def main():
    global SYSTEM_STATUS, SETTINGS
    while True:
        SETTINGS = read_settings()
        cur_temp = str(read_temp())
        cur_hr = str(read_hour())
        cur_time = str(read_time())
        toggle_target()

        
        if 7 <= float(cur_hr) < 9 or 15 <= float(cur_hr) < 21:

            print "high heat time"

            #check current temperature
            if not compare_temp(cur_temp):
                print "temp below target"
                if SYSTEM_STATUS != "on":
                    print "turning on"
                    turn_on()
                    SETTINGS['system_status'] = "on"
                else:
                    print "heat on."
                    
            else:
                if SYSTEM_STATUS != "off":
                    print "turning off"
                    turn_off()

                    SETTINGS['system_status'] = "off"
                else:
                    print "heat is off"

        else:
            print "low temp time"
            if float(cur_temp) < float(SETTINGS['target_low_temp']):
                if SYSTEM_STATUS != "on":
                    print "turning on"
                    turn_on()
                    SETTINGS['system_status'] = "on"
                else:
                    print "heat on"
            else:
                if SYSTEM_STATUS != "off":
                    print "turning off"
                    turn_off()
                    SETTINGS['system_status'] = "off"
                else:
                    print "heat off"

        SETTINGS['current_temp'] = cur_temp
        write_settings(SETTINGS)
        print cur_time+" : "+cur_temp
        log_temp()
        time.sleep(30)
    

if __name__ == "__main__":

    setup_GPIO()
    try:
        main()
    except KeyboardInterrupt:
        gpio.cleanup()
        print "Closing"
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
