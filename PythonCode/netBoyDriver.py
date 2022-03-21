# Driver Code for netBoy network analizer
# Author:   Aaron Hickman
# Version:  03.21.2022 
# Required apt repositories:    python3-rpi.gpio python3-pil python3-smbus python3-dev libopenjp2-7
# Required pip3 repositories:   gpiozero netifaces spidev rpi.gpio pillow
# Eink Display is 264x176 Pixels (For reference)



import socket  # importing socket to get the hostname
from datetime import datetime  # Import datetime for screen refresh time
from gpiozero import Button  # import the Button control from gpiozero
import netifaces as ni  # Importing netifaces to gather network information
import epd2in7  # Importing epd2in7 as the driver
from signal import pause  # Importing pause so the program waits for an input
from PIL import Image, ImageDraw, ImageFont  # Importing image things for processing
import subprocess # Used to run console commands efficently
import sys  # Used to make calls to the shell
import csv  # used to process csv files

# Program "Globals" and Initial Values

#getting juniper switch password from switches.csv
switchDataFile = "/home/ahickman/Documents/Python/netBoyEnv/netBoy/PythonCode/Data/switches.csv"
switches = list(csv.reader(open(switchDataFile)))

# Keys are assigned to the corresponding pin
key1 = Button(5)
key2 = Button(6)
key3 = Button(13)
key4 = Button(19)

#Intitial Screen values - to make them global
net_stats = ""
net_info = ""
net_stats = ""
cpu_info = ""
tools = ""

local_mac = ""
local_ip = ""

#fonts
font = ImageFont.truetype('Font.ttc', 18)  # Create our font, passing in the font file and font size
fontsmall = ImageFont.truetype('Font.ttc', 12)  # Create our font, passing in the font file and font size
fontsupersmall = ImageFont.truetype('Font.ttc', 8)  # Create our font, passing in the font file and font size


hostname = socket.gethostname() # device name

#Set up screen driver class
epd = epd2in7.EPD()  # get the display
epd.init()   # initialize the display
print("Clear...")  # prints to console, not the display, for debugging
epd.Clear()  # clear the display


def printLoading():
    HBlackImage = Image.new('1', (epd2in7.EPD_HEIGHT, epd2in7.EPD_WIDTH), 255)
    draw = ImageDraw.Draw(HBlackImage)  # Create draw object and pass in the image layer we want to work with (HBlackImage)
    draw.text((100, 60), "Loading...", font=fontsmall, fill=0)
    draw.rectangle((20, 250, 34, 176), outline=0)
    epd.display(epd.getbuffer(HBlackImage))

def printToDisplay(message):
    HBlackImage = Image.new('1', (epd2in7.EPD_HEIGHT, epd2in7.EPD_WIDTH), 255)
    draw = ImageDraw.Draw(HBlackImage)  # Create draw object and pass in the image layer we want to work with (HBlackImage)
    # Fonts with different sizes to be used
    draw.line((34, 22, 264, 22), fill=0)  # Draw top line
    draw.line((34, 23, 264, 23), fill=0)  # Draw top line (make thicker)
    draw.text((40, 2), message, font=fontsmall, fill=0)  # This is the overall Text
    # This is the bottom section of the screen with the date and time
    now = datetime.now()  # Gets the date and time now
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")  # Defines the layout of the datetime string
    draw.line((34, 158, 264, 158), fill=0)  # Draw bottom line
    draw.line((34, 159, 264, 159), fill=0)  # Draw bottom line (make thicker)
    draw.text((40, 160), f"LU:{dt_string}  [{getBatteryInfo()}]", font=fontsmall, fill=0)  # Date Time String at bottom
    # This is the left section of the screen with key descriptions
    draw.line((34, 0, 34, 180), fill=0)  # Draw Vertical Key lines
    draw.line((35, 0, 35, 180), fill=0)  # Draw Vertical Key lines (make thicker)
    draw.text((2, 2), f"""Network \nInfo """, font=fontsupersmall, fill=0)  # Key1 Text
    draw.rectangle((0, 0, 34, 44), outline=0)  # Boxes around the key1 description
    draw.text((2, 52), f"""Network \nStats """, font=fontsupersmall, fill=0)  # Key2 Text
    draw.rectangle((0, 44, 34, 88), outline=0)  # Boxes around the key2 description
    draw.text((2, 102), f"""CPU \nInfo """, font=fontsupersmall, fill=0)  # Key3 Text
    draw.rectangle((0, 88, 34, 132), outline=0)  # Boxes around the key3 description
    draw.text((2, 152), f"""System \nTools """, font=fontsupersmall, fill=0)  # Key4 Text
    draw.rectangle((0, 132, 34, 176), outline=0)  # Boxes around the key4 description

    epd.display(epd.getbuffer(HBlackImage))

def querySwitch(ips):
    outputs = []
    for ip in ips:
        command = "sshpass -p " + ip[1] + " ssh pi@" + ip[0] + " \"show ethernet-switching table | match " + local_mac + " \""
        output = subprocess.check_output(command, shell=True).decode(sys.stdout.encoding).strip()
        outputArray = " ".join(output.split()).split(" ")
        outputArray.append(ip[0])
        outputs.append(outputArray)
    return outputs

def getUpdatedNetworkInfo():
    net_info = f"""ETH0 INFORMATION\n\nHOSTNAME: {hostname}\n[ETH0]{getEth0Stats()}\n{getGateways()}"""
    return net_info

def switchInfo():
    print("getting switch info")
    portInfo = [['n/a','','','','n/a','n/a'],['n/a','','','','n/a','n/a']]
    try:
        portInfo = querySwitch(switches)
        print(portInfo)
    except Exception as e:
        portInfo = [['n/a','','','','n/a','n/a'],['n/a','','','','n/a','n/a']]
    net_stats = f"""Switch Info
    
    [Switch]: {portInfo[0][5]}
    [Port]: {portInfo[0][4]}
    [Vlan]: {portInfo[0][0]}
    [Switch]: {portInfo[1][5]}
    [Port]: {portInfo[1][4]}
    [Vlan]: {portInfo[1][0]}
    [Link Speed]: {getLinkSpeed()}
    """
    return net_stats

def getLinkSpeed():
    return subprocess.check_output("sudo ethtool eth0| grep \"Speed\"", shell=True).decode(sys.stdout.encoding).strip()

def getEth0Stats():
    try:
        local_mac = ni.ifaddresses('eth0')[ni.AF_LINK][0]['addr'] #eth0 mac address
        local_ip = ni.ifaddresses('eth0')[ni.AF_INET][0]['addr']  #eth0 ip address
    except Exception as e:
        local_ip = "not connected"
        local_mac = "not connected"
    return "\n\tMAC:" + local_mac + "\n\tIP:" + local_ip

def getGateways():
    
    return subprocess.check_output("route | grep -E '^default' | awk '{print $8" "$2}'", shell=True).decode(sys.stdout.encoding).strip()
def handleBtnPress(btn):
    printLoading()
    switcher = {
        5: f"updateInfo",
        6: f"switchInfo",
        13: f"updateInfo",
        19: f"switchInfo"
    }     
    # get the string based on the passed button and send it to printToDisplay()
    num = btn.pin.number
    if(num == 5 or num == 13):
        msg = getUpdatedNetworkInfo()
    elif(num == 6 or num == 19):
        msg = switchInfo()
    else:
        msg ="error"
    printToDisplay(msg)


def getBatteryInfo():
    return subprocess.check_output("echo \"get battery\" | nc -q 0 127.0.0.1 8423", shell=True).decode(sys.stdout.encoding).strip()



#Main Process
printToDisplay(getUpdatedNetworkInfo())  # Default screen

# tell the button what to do when pressed
key1.when_pressed = handleBtnPress
key2.when_pressed = handleBtnPress
key3.when_pressed = handleBtnPress
key4.when_pressed = handleBtnPress

pause()
