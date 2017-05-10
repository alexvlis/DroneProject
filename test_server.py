import io
import os
import socket
import struct
import time
import threading
import hashlib
import wave
import pickle
from threading import Thread

class Sensor(Thread):
    def __init__ (self):
        Thread.__init__(self)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def __del__ (self):
        self.connection.close()
        self.sock.close()

    def setup(self):
        self.sock.bind(('0.0.0.0', self.port))
        self.sock.listen(0)
        print "Listening on port", self.port, "..."
        # Accept a single connection and make a file-like object out of it
        (self.clientsocket, self.clientaddress) = self.sock.accept()
        self.connection = self.clientsocket.makefile('rb')

    def run(self):
        self.setport()
        self.setup()
        self.serve()

class Camera(Sensor):
    def setport(self):
        self.port = 81

    def serve(self):
        print "Receiving video..."
        try:
            while 1:
                # Read the length of the image as a 32-bit unsigned int. If the
                # length is zero, quit the loop
                image_len = struct.unpack('<L', self.connection.read(struct.calcsize('<L')))[0]
                if not image_len:
                    break
                data = self.connection.read(image_len)
                # Use a tmp file to minimize exposure to file blocking
                FILE = open("~tmp.jpeg", "w+")
                FILE.write(data)
                FILE.close()
                os.rename("~tmp.jpeg", "image.jpeg")
        except (socket.error, struct.error):
            print "ERROR: Connection to camera client lost!"

class Microphone(Sensor):
    def setport(self):
        self.port = 82

    def serve(self):
        print "Receiving audio..."
        try:
            while 1:
                length = struct.unpack('<L', self.connection.read(struct.calcsize('<L')))[0]
                if not length:
                    break
                FILE = wave.open('~tmp.wav', 'w')
                FILE.setnchannels(1)
                FILE.setsampwidth(2)
                FILE.setframerate(44100)
                FILE.writeframes(self.connection.read(length))
                FILE.close()
                os.rename("~tmp.wav", "sound.wav")
        except (socket.error, struct.error):
            print "ERROR: Connection to microphone client lost!"

class Radar(Sensor):
    def setport(self):
        self.port = 83

    def serve(self):
        print "Receiving radar feed..."
        try:
            while 1:
                FILE = open("~tmp.txt", "w+")
                length = struct.unpack('<L', self.connection.read(struct.calcsize('<L')))[0]
                if not length:
                    break
                FILE.write(self.connection.read(length))
                FILE.close()
                os.rename("~tmp.txt", "radar.txt")
        except (socket.error, struct.error):
            print "ERROR: Connection to radar client lost!"

class Ping(Sensor):
    def setport(self):
        self.port = 85

    def serve(self):
        print "Receiving ping sensor feed..."
        try:
            while 1:
                FILE = open("~tmp.txt", "w+")
                length = struct.unpack('<L', self.connection.read(struct.calcsize('<L')))[0]
                if not length:
                    break
                FILE.write(pickle.loads(self.connection.read(length)))
                FILE.close()
                os.rename("~tmp.txt", "ping.txt")
        except (socket.error):
            print "ERROR: Connection to ping client lost!"

def watch_GUI():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("10.100.1.106", 84))
        connection = sock.makefile('wb')
        prev_hash = 0
        while 1:
            FILE = open("GUI.txt", "r")
            md5_hash = hashlib.md5()
            md5_hash.update(FILE.readline())
            current_hash = md5_hash.hexdigest()

            if (current_hash != prev_hash):
                (direction, angle1, angle2, mode) = FILE.readline().split()
                connection.write(struct.pack('<h', direction))
                connection.flush()
                connection.write(struct.pack('<f', angle1))
                connection.flush()
                connection.write(struct.pack('<f', angle2))
                connection.flush()
                connection.write(struct.pack('<h', mode))
                connection.flush()
                prev_hash = current_hash

            del md5_hash
            FILE.close()
    except (socket.error, struct.error):
        print "ERROR: Could not write to motor socket!"
    finally:
        connection.close()

# Start of main program
if __name__ == "__main__":
    camera = Camera()
    microphone = Microphone()
    ping = Ping()
    #radar = Radar()

    # Daemonize the threads
    camera.daemon = True
    microphone.daemon = True
    ping.daemon = True
    #radar.daemon = True

    camera.start()
    microphone.start()
    ping.start()
    #radar.start()

    #watch_GUI()

    # Watcher for remaining threads
    while threading.active_count() > 1:
        time.sleep(0.1)
