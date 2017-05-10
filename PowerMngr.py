#!/usr/bin/python

import spidev

# Start of main program
if __name__ == "__main__":
    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 5000
    spi.mode = 0b01
    try:
        while 1:
            v1 = spi.readbytes(4)
            v2 = spi.readbytes(4)
            v3 = spi.readbytes(4)
            if (v1 >  ):
                spi.write(struct.pack('<h', 1))
            if (v2 >  ):
                spi.write(struct.pack('<h', 2))
            if (v3 >  ):
                spi.write(struct.pack('<h', 3))
    except:
        print "ERROR: Problem in SPI interface!"
