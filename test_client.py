#!/usr/bin/python

import socket
import os
import io
import time
import struct
import threading
import sys
import pickle
import RPi.GPIO as GPIO
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

class Ping(Sensor):
    def PingDistance(self,trigPin,echoPin):
        time.sleep(0.0005)
        GPIO.output(trigPin,GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(trigPin,GPIO.LOW)
        catchFailedEcho = time.time()
        while GPIO.input(echoPin) == 0:
            if time.time()- catchFailedEcho > 0.0001:
                return -1.0
            pass
        start = time.time()
        while GPIO.input(echoPin) == 1:
            if time.time()- catchFailedEcho > 0.0001:
                return -1.0
            pass
        stop = time.time()

        average = (stop - start)*17000

        if average >= 100.0:
            average = -1.0

        returning = average

        return  returning

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
                for TurnAngle in range(0,180,12):
                    self.ServoAngle(TurnAngle)
                    time.sleep(0.1)
                    Distance1 = self.PingDistance(self.TRIG1,self.ECHO1)
                    Distance2 = self.PingDistance(self.TRIG2,self.ECHO2)
                    Distance3 = self.PingDistance(self.TRIG3,self.ECHO3)
                    Distance4 = self.PingDistance(self.TRIG4,self.ECHO4)
                    data.append([TurnAngle, Distance1,Distance2,Distance3,Distance4])
                print data
                serialized = pickle.dumps(data)
                self.connection.write(struct.pack('<L', len(serialized)))
                self.connection.flush()
                self.connection.write(serialized)
                self.connection.flush()

                data = []
                for TurnAngle in range(180,0,-12):
                    self.ServoAngle(TurnAngle)
                    time.sleep(0.1)
                    Distance1 = self.PingDistance(self.TRIG1,self.ECHO1)
                    Distance2 = self.PingDistance(self.TRIG2,self.ECHO2)
                    Distance3 = self.PingDistance(self.TRIG3,self.ECHO3)
                    Distance4 = self.PingDistance(self.TRIG4,self.ECHO4)
                    data.append([TurnAngle, Distance1,Distance2,Distance3,Distance4])
                print data
                serialized = pickle.dumps(data)
                self.connection.write(struct.pack('<L', len(serialized)))
                self.connection.flush()
                self.connection.write(serialized)
                self.connection.flush()

        except socket.error:
            print "ERROR: Connection to ping server lost!"


# Start of main program
if __name__ == "__main__":
    ping = Ping()

    # Daemonize the threads
    ping.daemonize = True

    ping.start()

    # Watcher for remaining threads
    while threading.active_count() > 1:
        time.sleep(0.1)
