import socket               # Import socket module
import os
from argparse import ArgumentParser
import logging
import threading
import time
import sys
import json

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(level=logging.DEBUG,format=FORMAT)
LOG = logging.getLogger()

s = socket.socket()         # Create a socket object
host = socket.gethostname() # Get local machine name
port = 12348                 # Reserve a port for your service.
s.connect((host, port))
___NAME = 'HW2 Client'
___VER = '0.1.0.0'
___DESC = 'Simple TCP'
___BUILT = '2016-10-8'
___VENDOR = 'KeegiIkka'
def __info():
    return '%s version %s (%s) %s' % (___NAME, ___VER, ___BUILT, ___VENDOR)

def listen():
    while True:
        name = str(raw_input('Enter text to translate: '))
        if name == "exit":
            s.send(name)
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            print('Terminating client ...')
            sys.exit()
        else:
            t = threading.Thread(target=main, args=(name,))
            t.start()
            t.join()

def main(name):
    code = name.split(';')[0]
    if code == 'u':
        s.send(name)
        respo = s.recv(1024)
        print 'upload'
        if respo == 'okay':
            print "Passed here"
            s.send(name.split(';')[1])
        
        #while respo != 'Done':
        #    try:
        #        print "Next Sentence"
        #        print respo
        #        respo = s.recv(1024)
        #    except KeyboardInterrupt:
        #        print "Key interrupt"
        try:
            respo = s.recv(1024)
        except KeyboardInterrupt:
            print "Ended"
        enc = json.loads(respo, encoding='utf-8')
        print "This is final translation:"
        print enc['final_trans']
        print "This is the weightstuff"
        print enc['weights'][0]
        print "This is the preprocessed input"
        print enc['raw_input'][0]
        print "This is the un-processed output"
        print enc['raw_trans'][0]
        # print(respo)
    else:
        print('Incorrect control code ...')

t = threading.Thread(target=listen)
t.start()
t.join()
