""" PLC 1 """

from minicps.devices import PLC
from threading import Thread
from utils import *
from random import *
import logging
import json
import select
import socket
import time
import signal
import sys

Q101 = ('Q101', 1)
Q102 = ('Q102', 1)

LIT101 = ('LIT101', 1)
LIT102 = ('LIT102', 1)
LIT103 = ('LIT103', 1)


class PLC101(PLC):

    def send_message(self, ipaddr, port, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ipaddr, port))

        msg_dict = dict.fromkeys(['Type', 'Variable'])
        msg_dict['Type'] = "Report"
        msg_dict['Variable'] = message
        message = json.dumps(str(msg_dict))

        try:
            ready_to_read, ready_to_write, in_error = select.select([sock, ], [sock, ], [], 5)

        except:
            print "Socket error"
            return

        if(ready_to_write > 0):
            sock.send(message)
            print "At count ", self.count
            print "Sending to the pump:", message

        sock.close()


    def recv_message(self, ipaddr, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ipaddr, port))

        try:
            ready_to_read, ready_to_write, in_error = select.select([sock, ], [sock, ], [], 5)
            
        except:
            print "Socket error"
            return
          
        if(ready_to_read > 0):
            data = sock.recv(4096)
            encoded_data = data.decode()
            message_dict = eval(json.loads(data))
            received_level = float(message_dict['Variable'])
            sock.close()
            
            print "At count ", self.count
            print "Received level is: ", received_level
            return received_level


    def change_references(self):

            if self.count <= 50:
                    self.ref_y0 = 0.4
            if self.count > 50 and self.count <= 350:
                    self.ref_y0 = 0.450
            if self.count > 350:
                    self.ref_y0 = 0.4

            if self.count <= 70:
                    self.ref_y1 = 0.2
            if self.count > 70 and self.count <= 400:
                    self.ref_y1 = 0.225
            if self.count > 400:
                    self.ref_y1 = 0.2

    def sigint_handler(self, sig, frame):
        print "I received a SIGINT!"
        sys.exit(0)

    def pre_loop(self, sleep=0.1):
        print 'DEBUG: swat-s1 plc1 enters pre_loop'
        signal.signal(signal.SIGINT, self.sigint_handler)
        signal.signal(signal.SIGTERM, self.sigint_handler)
        logging.basicConfig(filename="plc.log", level=logging.DEBUG)

        # Controller Initial Conditions
        self.count = 0

        self.ref_y0 = Y10
        self.ref_y1 = Y20

        self.lit101 = 0.0
        self.lit102 = 0.0
        lit103 = 0.0
        self.lit103 = 0.0

        self.q1 = 0.0
        self.q2 = 0.0

        self.received_lit101 = 0.0
        self.received_lit102 = 0.0
        received_lit103 = 0.0
        self.received_lit103 = 0.0

        self.z =  np.array([[0.0],[0.0]], )
        self.current_inc_i = np.array([[0.0],[0.0]])
        self.K1K2 = np.concatenate((K1,K2),axis=1)

        
    def main_loop(self):
        """ plc1 main loop.
            - reads sensors value
            - drives actuators according to the control strategy
            - updates its enip server
        """

        print 'DEBUG: swat-s1 plc1 enters main_loop.'
        
        while(self.count <= PLC_SAMPLES):
          try:
            self.change_references()
            print "Count: ", self.count, "ref_y0: ", self.ref_y0
            
            logging.debug('At count %d:', self.count)
            logging.debug('Reference level for Tank1 is %f', self.ref_y0)
            self.received_lit101 = self.recv_message(IP['lit101'], 8754)
            self.received_lit102 = self.recv_message(IP['lit102'], 8754)
            #self.received_lit103 = self.recv_message(IP['lit103'], 8754)
            
            #print "The received levels from the sensors are: ", self.received_lit101, self.received_lit102
            logging.debug('Received levels from 1 and 2 sensors: %s , %s', self.received_lit101, self.received_lit102)
            
            #self.received_lit101 = float(self.receive(LIT101, SENSOR_ADDR))
            #self.received_lit101 = float(self.get(LIT101))
            self.lit101 = self.received_lit101 - Y10
            
            #xhat is the vector used for the controller. In the next version, xhat shouldn't be read from sensors, but from luerenberg observer
            #self.received_lit102 = float(self.get(LIT102))
            self.lit102 = self.received_lit102 - Y20
            
            received_lit103 = float(self.get(LIT103))
            lit103 = received_lit103 - Y30
            
            self.lit101_error = self.ref_y0 - self.received_lit101
            self.lit102_error = self.ref_y1 - self.received_lit102
            #print "Error: ", self.lit101_error, " ", self.lit102_error
            
            #print lit101, lit102,lit103
            #set sequence numbers
            
            # Z(k+1) = z(k) + error(k)
            self.z[0,0] = self.z[0,0] + self.lit101_error
            self.z[1,0] = self.z[1,0] + self.lit102_error
            
            # xhat should be xhat(t) = xhat(t) - xhat(-1)
            #self.xhat= np.array([[self.lit101],[self.lit102],[self.lit103]])
            self.xhat= np.array([[self.lit101],[self.lit102],[lit103]])
            self.xhatz=np.concatenate((self.xhat,self.z), axis=0)
            #print "xhatz: ", self.xhatz
            
            self.current_inc_i = np.matmul(-self.K1K2,self.xhatz)
            
            self.q1 = Q1 + self.current_inc_i[0]
            self.q2 = Q2 + self.current_inc_i[1]
            #print "Cumulative inc: ", " ", self.current_inc_i[0], " ", self.current_inc_i[1]
            #print "Sending to actuators: ", " ", self.q1, " ", self.q2
            
            #self.set(Q101, float(self.q1))
            #self.set(Q102, float(self.q2))
            self.send_message(IP['q101'], 7842 ,float(self.q1))
            self.send_message(IP['q102'], 7842 ,float(self.q2))
            
            #print "Sending to q101:", self.q1
            #print "Sending to q102:", self.q2
            
            logging.debug('Q1 value to be sent to pump 1: %s', self.q1)
            logging.debug('Q2 value to be sent to pump 2: %s', self.q2)
            
            self.count += 1
            time.sleep(PLC_PERIOD_SEC)
    
          except Exception as e:
            print e
            print "Switching to backup"
            break

if __name__ == "__main__":
    plc101 = PLC101(name='plc101',state=STATE,protocol=PLC101_PROTOCOL,memory=GENERIC_DATA,disk=GENERIC_DATA)
