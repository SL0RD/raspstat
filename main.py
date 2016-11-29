import os
import glob
import time
import RPi.GPIO as GPIO
import sys
import json

GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
green_led = 11
red_led = 15
relay = 13

base_dir='/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder+ '/w1_slave'

SETTINGS_FILE = 'settings.json'
SYSTEM_STATUS = None
SETTINGS = None


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
    if float(7) <= float(cur_hr) < float(21):
        if SETTINGS['current_target'] != SETTINGS['target_high_temp']:
            SETTINGS['current_target'] = SETTINGS['target_high_temp']
    elif float(17) <= float(cur_hr) < float(21):
        if SETTINGS['current_target'] != SETTINGS['target_high_temp']:
            SETTINGS['current_target'] = SETTINGS['target_high_temp']
    else:
        if SETTINGS['current_target'] != SETTINGS['target_low_temp']:
            SETTINGS['current_target'] = SETTINGS['target_low_temp']
    write_settings(SETTINGS)


def turn_on():
    global SYSTEM_STATUS
    SYSTEM_STATUS = "on"
    GPIO.output(11, GPIO.HIGH)
    GPIO.output(13, GPIO.HIGH)
    GPIO.output(15, GPIO.LOW)


def turn_off():
    global SYSTEM_STATUS
    SYSTEM_STATUS = "off"
    GPIO.output(11, GPIO.LOW)
    GPIO.output(13, GPIO.LOW)
    GPIO.output(15, GPIO.HIGH)

def main():
    global SYSTEM_STATUS, SETTINGS
    while True:
        SETTINGS = read_settings()
        cur_temp = str(read_temp())
        cur_hr = str(read_hour())
        cur_time = str(read_time())
        toggle_target()
        if 7 <= float(cur_hr) < 21 or 17 <= float(cur_hr) < 21:

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
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        GPIO.cleanup()
        print "Closing"
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
