from enum import IntFlag
from functools import reduce
import spidev

    
class LS7366R:
    # The possible count modes the modules can use.
    class CountMode(IntFlag):
        NoneQuad = 0 # Non-quadrature mode
        Quad1 = 1 # 1x quadrature mode
        Quad2 = 2 # 2x quadrature mode
        Quad4 = 3 # 4x quadrature mode

    class Commands(IntFlag):
        LS7366_CLEAR = 0x00 # clear register
        LS7366_READ = 0x40 # read register
        LS7366_WRITE = 0x80 # write register
        LS7366_LOAD = 0xC0 # load register

    class Registers(IntFlag):
        LS7366_MDR0 = 0x08 # select MDR0
        LS7366_MDR1 = 0x10 # select MDR1
        LS7366_DTR = 0x18 # select DTR
        LS7366_CNTR = 0x20 # select CNTR
        LS7366_OTR = 0x28 # select OTR
        LS7366_STR = 0x30 # select STR

    class MDR0Mode(IntFlag):
        LS7366_MDR0_QUAD0 = 0x00 # none quadrature mode
        LS7366_MDR0_QUAD1 = 0x01 # quadrature x1 mode
        LS7366_MDR0_QUAD2 = 0x02 # quadrature x2 mode
        LS7366_MDR0_QUAD4 = 0x03 # quadrature x4 mode

        LS7366_MDR0_FREER = 0x00 # free run mode
        LS7366_MDR0_SICYC = 0x04 # single cycle count mode
        LS7366_MDR0_RANGE = 0x08 # range limit count mode (0-DTR-0)
        # counting freezes at limits but 
        # resumes on direction reverse
        LS7366_MDR0_MODTR = 0x0C # modulo-n count (n=DTR both dirs)

        LS7366_MDR0_DIDX = 0x00 # disable index
        LS7366_MDR0_LDCNT = 0x10 # config IDX as load DTR to CNTR
        LS7366_MDR0_RECNT = 0x20 # config IDX as reset CNTR (=0)
        LS7366_MDR0_LDOTR = 0x30 # config IDX as load CNTR to OTR  

        LS7366_MDR0_ASIDX = 0x00 # asynchronous index
        LS7366_MDR0_SYINX = 0x40 # synchronous IDX (if !NQUAD)

        LS7366_MDR0_FFAC1 = 0x00 # filter clock division factor=1
        LS7366_MDR0_FFAC2 = 0x80 # filter clock division factor=2

        LS7366_MDR0_NOFLA = 0x00 # no flags

    class MDR1Mode(IntFlag):
        LS7366_MDR1_4BYTE = 0x00 # 4 byte counter mode
        LS7366_MDR1_3BYTE = 0x01 # 3 byte counter mode
        LS7366_MDR1_2BYTE = 0x02 # 2 byte counter mode
        LS7366_MDR1_1BYTE = 0x03 # 1 byte counter mode
        LS7366_MDR1_ENCNT = 0x00 # enable counting
        LS7366_MDR1_DICNT = 0x04 # disable counting
        LS7366_MDR1_FLIDX = 0x10
        LS7366_MDR1_FLCMP = 0x20
        LS7366_MDR1_FLBW = 0x40
        LS7366_MDR1_FLCY = 0x80
        
    def __init__(self, spi_cs_line=0, spi_max_speed_hz=1000000, reverse=False):
        self.quadrature_mode = None
        self.reverse = reverse

        self.spi = spidev.SpiDev()
        self.spi.open(0, spi_cs_line)
        self.spi.max_speed_hz = spi_max_speed_hz

        self._initialize()

    def _initialize(self):
        self.write1(LS7366R.Commands.LS7366_CLEAR | LS7366R.Registers.LS7366_MDR0)
        self.write1(LS7366R.Commands.LS7366_CLEAR | LS7366R.Registers.LS7366_MDR1)
        self.write1(LS7366R.Commands.LS7366_CLEAR | LS7366R.Registers.LS7366_STR)
        self.write1(LS7366R.Commands.LS7366_CLEAR | LS7366R.Registers.LS7366_CNTR)
        self.write1(LS7366R.Commands.LS7366_LOAD | LS7366R.Registers.LS7366_OTR)

        self.set_quadrature_mode(LS7366R.CountMode.Quad1)
        self._write2(LS7366R.Commands.LS7366_WRITE | LS7366R.Registers.LS7366_MDR1, LS7366R.MDR1Mode.LS7366_MDR1_4BYTE | LS7366R.MDR1Mode.LS7366_MDR1_ENCNT)

    def close(self):
        self.spi.close()

    # Gets the current count from the module.
    def read_counter(self):
        self.write1(LS7366R.Commands.LS7366_LOAD | LS7366R.Registers.LS7366_OTR)
        counter = self._read(LS7366R.Commands.LS7366_READ | LS7366R.Registers.LS7366_OTR)
        counter = counter if counter < 0x80000000 else counter - 0xFFFFFFFF # to signed
        return counter if not self.reverse else -counter

    # Resets the count on the module to 0.
    def reset_counter(self):
        self.write1(LS7366R.Commands.LS7366_CLEAR | LS7366R.Registers.LS7366_CNTR)

    # Sets the count mode the module uses.
    def set_quadrature_mode(self, quadrature_mode):
        if self.quadrature_mode == quadrature_mode:
            return

        self.quadrature_mode = quadrature_mode

        command = LS7366R.MDR0Mode.LS7366_MDR0_FREER | LS7366R.MDR0Mode.LS7366_MDR0_DIDX | LS7366R.MDR0Mode.LS7366_MDR0_FFAC2 | {
                LS7366R.CountMode.NoneQuad: LS7366R.MDR0Mode.LS7366_MDR0_QUAD0,
                LS7366R.CountMode.Quad1: LS7366R.MDR0Mode.LS7366_MDR0_QUAD1,
                LS7366R.CountMode.Quad2: LS7366R.MDR0Mode.LS7366_MDR0_QUAD2,
                LS7366R.CountMode.Quad4: LS7366R.MDR0Mode.LS7366_MDR0_QUAD4,
            }[self.quadrature_mode]

        self._write2(LS7366R.Commands.LS7366_WRITE | LS7366R.Registers.LS7366_MDR0, command)

    def _read(self, register):
        data = [register] + [0] * 4 # 4 = byte mode
        data = self.spi.xfer2(data)
        return reduce(lambda a,b: (a<<8) + b, data[1:], 0)
        #return (data[1] << 24) + (data[2] << 16) + (data[3] << 8) + data[4]

    def write1(self, register):
        self.spi.xfer2([register])

    def _write2(self, register, command):
        self.spi.xfer2([register, command])


if __name__ == "__main__":
    from time import sleep
    import sys

    counter = LS7366R(0, 1000000)
    try:
        while True:
            sys.stdout.write('\rEncoder count: %11i CTRL+C for exit' % counter.read_counter())
            sys.stdout.flush()
            sleep(0.2)
    except KeyboardInterrupt:
        counter.close()
        print("Done")
