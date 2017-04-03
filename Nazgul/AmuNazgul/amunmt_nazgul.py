#!/usr/bin/env python
'''
Translates a source file using a translation model.
'''
import codecs
import logging
import socket
import threading
import sys
import os
import argparse

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../build/src')
import libamunmt as nmt
from nltk.tokenize import moses, sent_tokenize

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(level=logging.DEBUG,format=FORMAT)
LOG = logging.getLogger()
DUMP_DIR = '/home/osboxes/PycharmProjects/DShw4/DumpFolder/'

def parallelized_main(c, tokenizer, detokenizer, tokenize):
    print tokenize
    gotthis = c.recv(4096)
    source_file_t = sent_tokenize(gotthis)
    if tokenize:
        for i in range(len(source_file_t)):
            source_file_t[i] = str(tokenizer.tokenize(source_file_t[i], return_str=True))
    while source_file_t[0] != "EOT":
        detokenized = ''
        trans = nmt.translate(source_file_t)
        print trans
        if tokenize:
            for i in trans:
                detokenized_par = detokenizer.detokenize((i.decode('utf-8') + " ").split(), return_str=True)
                detokenized += detokenized_par[0].upper() + detokenized_par[1:]
        else:
            for i in trans:
                detokenized_par = i.decode('utf-8') + " "
                detokenized += detokenized_par[0].upper() + detokenized_par[1:]
        c.send(detokenized.replace('@@ ', '').encode('utf-8').strip())
        source_file_t = sent_tokenize(c.recv(4096))
    c.close()
    sys.stderr.write('Done\n')

def listen(c, addr, tokenizer, detokenizer, tokenize):
    while True:
        try:  # Establish connection with client.
            try:
                print 'Got connection from', addr
                print "Receiving..."
                fname = c.recv(4096)
            except socket.error:
                c.close()
                print "connection closed"
                break
            print fname
            c.send("okay")
            try:
                t = threading.Thread(target=parallelized_main,
                                     args=(c, tokenizer, detokenizer, tokenize))
                t.start()
                t.join()
            except socket.error:
                c.close()
                break
        except KeyboardInterrupt as e:
            LOG.debug('Crtrl+C issued ...')
            LOG.info('Terminating server ...')
            try:
                c.shutdown(socket.SHUT_RDWR)
                c.close()
            except:
                pass
            break

def main(tokenize):
    s = socket.socket()  # Create a socket object
    host = socket.gethostname()  # Get local machine name
    port = 12345  # Reserve a port for your service.
    s.bind((host, port))  # Bind to the port #  Now wait for client connection.
    tokenizer = moses.MosesTokenizer()
    detokenizer = moses.MosesDetokenizer()
    while True:
        try:
            s.listen(5)
            print("Waiting for connections and stuff...")
            c, addr = s.accept()
            t = threading.Thread(target=listen,
                                 args=(c, addr, tokenizer, detokenizer, tokenize))
            t.start()
        except KeyboardInterrupt:
            break
    s.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", dest="config")
    parser.add_argument('--tokenize', '-t', type=bool, default=False,
                        help="Should the server tokenize input (default: True")
    args = parser.parse_args()

    ## MODEL LOADED HERE
    nmt.init("-c {}".format(args.config))
    main(args.tokenize)
