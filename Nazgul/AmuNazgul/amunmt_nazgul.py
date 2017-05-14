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
import re

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../build/src')
import libamunmt as nmt
from collections import defaultdict
from nltk.tokenize import moses, sent_tokenize

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
LOG = logging.getLogger()
DUMP_DIR = '/home/osboxes/PycharmProjects/DShw4/DumpFolder/'


def truecasing(truecaser, word):
    result = truecaser[word.lower()]
    if len(result) > 0:
        return result
    else:
        return word


def pre_processing(tokenize, tokenizer, truecaser, received):
    # SPLIT THE WHITESPACES
    source_file_t = re.split('([\t\n\r\f\v]+)', received)

    # SENTENCE TOKENIZE
    for i in range(len(source_file_t)):
        if i % 2 == 0:
            source_file_t[i] = sent_tokenize(source_file_t[i])

    # TOKENIZATION
    if tokenize:
        for j in range(len(source_file_t)):
            if j % 2 == 0:
                for i in range(len(source_file_t[j])):
                    try:
                        source_file_t[j][i] = str(
                            tokenizer.tokenize(source_file_t[j][i], return_str=True).encode('utf-8'))
                    except NameError:
                        source_file_t[j][i] = str(' '.join(source_file_t[j][i].split('.') + ['.']))

    # TRUECASING
    for j in range(len(source_file_t)):
        if j % 2 == 0:
            for i in range(len(source_file_t[j])):
                source_file_t[j][i] = str((truecasing(truecaser, source_file_t[j][i].split(' ')[0]).decode(
                    'utf-8') + " " + (' '.join(source_file_t[j][i].split(' ')[1:]).decode('utf-8'))).encode('utf-8'))
                print source_file_t[j][i]
                # except IndexError:
                #    print "Error occured"
                #    print source_file_t[j]
    return source_file_t


def parallelized_main(c, tokenizer, detokenizer, tokenize, truecaser):
    print tokenize
    gotthis = c.recv(4096).decode('utf-8')
    source_file_t = pre_processing(tokenize, tokenizer, truecaser, gotthis)
    try:
        while source_file_t[0][0] != "EOT":
            detokenized = ''
            trans = []
            for j in range(len(source_file_t)):
                if j % 2 == 0:
                    for i in source_file_t[j]:
                        trans += nmt.translate([i])
                else:
                    trans[-1] += str(source_file_t[j])
            # print trans
            # print source_file_t
            if tokenize:
                for i in trans:
                    # print i
                    splitting = re.split('([\t\n\r\f\v]+)', i)
                    # print splitting
                    for j in range(len(splitting)):
                        if j % 2 == 0:
                            try:
                                detokenized_par = detokenizer.detokenize((splitting[j].decode('utf-8') + " ").split(),
                                                                         return_str=True)
                                detokenized += detokenized_par[0].upper() + detokenized_par[1:] + " "
                            except IndexError:
                                pass
                        else:
                            detokenized += splitting[j]
            else:
                for i in trans:
                    detokenized_par = i.decode('utf-8') + " "
                    detokenized += detokenized_par[0].upper() + detokenized_par[1:]
            # print detokenized.replace('@@ ', '').encode('utf-8').strip()
            print detokenized.replace('@@ ', '').encode('utf-8')
            c.send(detokenized.replace('@@ ', '').encode('utf-8').strip())
            gotthis = c.recv(4096).decode('utf-8')
            source_file_t = pre_processing(tokenize, tokenizer, truecaser, gotthis)
        c.close()
        sys.stderr.write('Done\n')
    except IndexError:
        c.close()
        sys.stderr.write('Bad connecntion made\n')


def listen(c, addr, tokenizer, detokenizer, tokenize, truecaser):
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
            try:
                c.send("okay")
                t = threading.Thread(target=parallelized_main,
                                     args=(c, tokenizer, detokenizer, tokenize, truecaser))
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


def main(tokenize, truecase, sock):
    s = socket.socket()  # Create a socket object
    host = socket.gethostname()  # Get local machine name
    port = sock  # Reserve a port for your service.
    s.bind((host, port))  # Bind to the port #  Now wait for client connection.

    with codecs.open(truecase, 'r', encoding='utf-8') as f:
        tc_init = f.read().split('\n')

    truecaser = defaultdict(str)
    for line in tc_init:
        truecaser[line.split(' ')[0].lower()] = line.split(' ')[0]

    tokenizer = moses.MosesTokenizer()
    detokenizer = moses.MosesDetokenizer()
    while True:
        try:
            s.listen(5)
            print("Waiting for connections and stuff...")
            c, addr = s.accept()
            t = threading.Thread(target=listen,
                                 args=(c, addr, tokenizer, detokenizer, tokenize, truecaser))
            t.start()
        except KeyboardInterrupt:
            break
    s.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", dest="config")
    parser.add_argument('--tokenize', '-t', type=bool, default=False,
                        help="Should the server tokenize input (default: True")
    parser.add_argument("-e", dest="truecase")
    parser.add_argument("-s", dest="socket", type=int, default=12345)
    args = parser.parse_args()

    ## MODEL LOADED HERE
    nmt.init("-c {}".format(args.config))
    main(args.tokenize, args.truecase, args.socket)
