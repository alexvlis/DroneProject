#!/usr/bin/python

import socket
import picamera
import os
import io
import time
import struct
import alsaaudio
import threading
import hashlib
import sys
import pickle
#import visa
import RPi.GPIO as GPIO
import csv
from time import sleep
from threading import Thread

# Definition of classes
class SensorError(Exception):
    def __init__ (self, value):
        self.value = value
    def __str__ (self):
        return repr(self.value)

class Server():
    def __init__(self, addr, port):
        self.addr = addr
        self.port = port

class Sensor(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.server = Server("192.254.0.191", 0)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.detected = False

    def __del__(self):
        self.sock.close()

    def connect(self):
        try:
            self.sock.connect((self.server.addr, self.server.port))
        except socket.error:
            print "ERROR: Could not connect to server!"
            raise SensorError(-1)
        self.connection = self.sock.makefile('wb')

    def run(self):
        try:
            self.setup()
            self.connect()
        except SensorError as error:
            print "ERROR: Sensor exception occured with value", error.value
        else:
            self.serve()

class Camera(Sensor):

    def setup(self):
        try:
            self.__camera = picamera.PiCamera()
            self.server.port = 81
            self.__camera.resolution = (1280, 720)
            self.__camera.brightness = 60
            self.__camera.sharpness = 50
            self.__camera.shutterspeed = 0
            self.__camera.vflip = True
        except (picamera.PiCameraError, picamera.PiCameraValueError):
            print "ERROR: Camera not connected!"
            raise SensorError(-2)


    def serve(self):
        # Warm up the camera for 2 seconds
        print "Warming up the camera..."
        self.__camera.start_preview()
        sleep(2)
        self.__camera.stop_preview()

        stream = io.BytesIO()
        print "Streaming video..."
        # Stream frames forever
        try:
            for foo in self.__camera.capture_continuous(stream, 'jpeg',
                                                        use_video_port=True):
                # Write the length of the capture to the stream and flush to
                # ensure it actually gets sent
                self.connection.write(struct.pack('<L', stream.tell()))
                self.connection.flush()

                # Rewind the stream and send the image data over the wire
                stream.seek(0)
                self.connection.write(stream.read())
                self.connection.flush()
                # Reset the steam
                stream.seek(0)
                stream.truncate()
        except (socket.error, struct.error):
            print "ERROR: Connection to camera server lost!"
        except (picamera.PiCameraError, picamera.PiCameraValueError):
            print "ERROR: Could not capture from camera!"
        finally:
            self.__camera.close()

class Radar(Sensor):
    def setup(self):
        self.server.port = 83
        try:
            rm = visa.ResourceManager()
            rdkVisa = rm.open_resource("USB0::0x2012::0x0013::0022::0::INSTR")
        except:
            print "ERROR: Could not open radar!"
            raise SensorError(-2)

    def serve(self):
        try:
            while 1:
                rdkVisa.write("CAPT:FRAM 4096\n")
                data = rdkVisa.query("CAPT:FRAM?\n")
                self.connection.write(struct.pack('<L', len(data)))
                self.connection.flush()
                self.connection.write(data)
                self.connection.flush()
        except socket.error:
            print "ERROR: Could not write to radar socket!"
        except:
            print "ERROR: Could not capture radar frame!"


class Microphone(Sensor):
    def setup(self):
        try:
            self.server.port = 82
            self.__gomic = alsaaudio.PCM(type=alsaaudio.PCM_CAPTURE,
                                        mode=alsaaudio.PCM_NORMAL,
                                        card='hw:GoMic,0')
            self.__gomic.setchannels(1)
            self.__gomic.setrate(44100)
            self.__gomic.setformat(alsaaudio.PCM_FORMAT_S16_LE)
            self.__gomic.setperiodsize(2000)
        except alsaaudio.ALSAAudioError:
            print "ERROR: Gomic microphone is not connected!"
            raise SensorError(-2)

    def serve(self):
        print "Streaming audio..."
        try:
            while 1:
                sound = None
                for n in range(1, 50):
                    (length, data) = self.__gomic.read()
                    sound = sound + data
                self.connection.write(struct.pack('<L', len(sound)))
                self.connection.flush()
                self.connection.write(data)
                self.connection.flush()
        except socket.error:
            print "ERROR: Connection to microphone server lost!"
        except alsaaudio.ALSAAudioError:
            print "ERROR: Could not read from microphone!"

class Ping(Sensor):
    def PingDistance(self,trigPin,echoPin):
        GPIO.output(trigPin,GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(trigPin,GPIO.LOW)
        catchFailedEcho = time.time()
        while GPIO.input(echoPin) == 0:
            if time.time()- catchFailedEcho > 0.5:
                return -1.0
            pass
        start = time.time()
        while GPIO.input(echoPin) == 1:
            if time.time()- catchFailedEcho > 0.5:
                return -1.0
            pass
        stop = time.time()

        average = (stop - start)*17000

        if average >= 100.0:
            average = -1.0

        returning = average

        return int(round(returning))

    def setup(self):
        self.server.port = 85
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setwarnings(False)

            self.FULLZERO = 2.5
            self.FULLOPPOSITE = 12
            self.SERVOPIN = 18
            self.TRIG1 = 3
            self.TRIG2 = 5
            self.TRIG3 = 7
            self.TRIG4 = 11
            self.ECHO1 = 8
            self.ECHO2 = 10
            self.ECHO3 = 12
            self.ECHO4 = 16
            GPIO.setup(self.SERVOPIN,GPIO.OUT)
            GPIO.setup(self.TRIG1,GPIO.OUT)
            GPIO.output(self.TRIG1,GPIO.LOW)
            GPIO.setup(self.TRIG2,GPIO.OUT)
            GPIO.output(self.TRIG2,GPIO.LOW)
            GPIO.setup(self.TRIG3,GPIO.OUT)
            GPIO.output(self.TRIG3,GPIO.LOW)
            GPIO.setup(self.TRIG4,GPIO.OUT)
            GPIO.output(self.TRIG4,GPIO.LOW)
            GPIO.setup(self.ECHO1,GPIO.IN)
            GPIO.setup(self.ECHO2,GPIO.IN)
            GPIO.setup(self.ECHO3,GPIO.IN)
            GPIO.setup(self.ECHO4,GPIO.IN)

            self.pwm = GPIO.PWM(self.SERVOPIN,50)
            self.pwm.start(self.FULLZERO)
        except:
            print "ERROR: Could not setup ping sensor!"

    def ServoAngle(self, desiredAngle):
        DutyCycle = (desiredAngle*((self.FULLOPPOSITE- self.FULLZERO)/180)) + self.FULLZERO
        self.pwm.ChangeDutyCycle(DutyCycle)
        return

    def serve(self):
        print "Streaming ping feed..."
        try:
            while 1:
                data = []
                for TurnAngle in range(30,150,20):
                    sleep(0.1)
                    self.ServoAngle(TurnAngle)
                    Distance1 = self.PingDistance(self.TRIG1,self.ECHO1)
                    Distance2 = self.PingDistance(self.TRIG2,self.ECHO2)
                    Distance3 = self.PingDistance(self.TRIG3,self.ECHO3)
                    Distance4 = self.PingDistance(self.TRIG4,self.ECHO4)
                    data.append([TurnAngle, Distance1,Distance2,Distance3,Distance4])
                serialized = pickle.dumps(data)
                self.connection.write(struct.pack('<L', len(serialized)))
                self.connection.flush()
                self.connection.write(serialized)
                self.connection.flush()

                data = []
                for TurnAngle in range(150,30,-20):
                    sleep(0.1)
                    self.ServoAngle(TurnAngle)
                    Distance1 = self.PingDistance(self.TRIG1,self.ECHO1)
                    Distance2 = self.PingDistance(self.TRIG2,self.ECHO2)
                    Distance3 = self.PingDistance(self.TRIG3,self.ECHO3)
                    Distance4 = self.PingDistance(self.TRIG4,self.ECHO4)
                    data.append([TurnAngle, Distance1,Distance2,Distance3,Distance4])
                serialized = pickle.dumps(data)
                self.connection.write(struct.pack('<L', len(serialized)))
                self.connection.flush()
                self.connection.write(serialized)
                self.connection.flush()
        except socket.error:
            print "ERROR: Connection to ping server lost!"


def watch_Motors():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', 84))
    sock.listen(0)
    (guisocket, guiaddress) = sock.accept()
    connection = guisocket.makefile('rb')
    try:
        while 1:
            direction = struct.unpack('<h', connection.read(struct.calcsize('<h')))[0]
            angle1 = struct.unpack('<h', connection.read(struct.calcsize('<h')))[0]
            angle2 = struct.unpack('<h', connection.read(struct.calcsize('<h')))[0]
            mode = struct.unpack('<h', connection.read(struct.calcsize('<h')))[0]

            FILE = open("motor.txt", "w")
            FILE.seek(0)
            FILE.write(str(direction))
            FILE.write("\n")
            FILE.write(str(angle1))
            FILE.write("\n")
            FILE.write(str(angle2))
            FILE.write("\n")
            FILE.write(str(mode))
            FILE.truncate()
            FILE.close()
    except (socket.error, struct.error):
        print "ERROR: Could not read motor control socket!"
    finally:
        connection.close()

# Start of main program
if __name__ == "__main__":
    camera = Camera()
    microphone = Microphone()
    #radar = Radar()
    ping = Ping()

    # Daemonize the threads
    camera.daemon = True
    ping.daemon = True
    #radar.daemon = True
    microphone.daemon = True

    camera.start()
    microphone.start()
    ping.start()
    #radar.start()

    watch_Motors()

    # Watcher for remaining threads
    while threading.active_count() > 1:
        time.sleep(0.1)
