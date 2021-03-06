from minicps.devices import PLC
from utils1 import *

import time
from threading import Thread

import socket
import json
import select
import logging


PLC101_ADDR = IP['plc201']

Q202 = ('Q202', 1)

class PSocket(Thread):
    """ Class that receives water level from the water_tank.py  """

    def __init__(self, plc_object):        
        Thread.__init__(self)
        self.plc = plc_object
	self.q202 = 0

    def run(self):
        print "DEBUG entering socket thread run"
        self.sock = socket.socket()     # Create a socket object    
        self.sock.bind((IP['q202'] , 7844 ))
        self.sock.listen(5)

        while True:
            try:
                client, addr = self.sock.accept()
                data = client.recv(4096)                             # Get data from the client         

                message_dict = eval(json.loads(data))
                self.q202 = float(message_dict['Variable'])

                #print "received from PLC101!", self.q202 
                logging.debug('Q2 level received from plc is %s', self.q202)
		self.plc.set(Q202, self.q202)

            except KeyboardInterrupt:
                print "\nCtrl+C was hitten, stopping server"
                client.close()
                break

class PP202(PLC):
        def pre_loop(self, sleep=0.1):
                print 'DEBUG: q202 enters pre_loop'
                time.sleep(sleep)
                logging.basicConfig(filename="q202.log", level=logging.DEBUG)

        def main_loop(self):
                print 'DEBUG: q202 enters main_loop'
                psocket = PSocket(self)
                psocket.start()

if __name__ == '__main__':
	q202 = PP202(name='q202',state=STATE,protocol=Q202_PROTOCOL,memory=GENERIC_DATA,disk=GENERIC_DATA)
