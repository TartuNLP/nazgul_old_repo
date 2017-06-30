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
import json

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


def pre_processing(tokenizer, truecaser, info):
    # SPLIT THE WHITESPACES
    source_file_t = re.split('([\t\n\r\f\v]+)', info['src'])

    # SENTENCE TOKENIZE
    for i in range(len(source_file_t)):
        if i % 2 == 0:
            source_file_t[i] = sent_tokenize(source_file_t[i])

    # TOKENIZATION
    if info['tok']:
        for j in range(len(source_file_t)):
            if j % 2 == 0:
                for i in range(len(source_file_t[j])):
                    try:
                        source_file_t[j][i] = str(
                            tokenizer.tokenize(source_file_t[j][i], return_str=True).encode('utf-8'))
                    except NameError:
                        source_file_t[j][i] = str(' '.join(source_file_t[j][i].split('.') + ['.']))

    # TRUECASING
    if info['tc']:
        for j in range(len(source_file_t)):
            if j % 2 == 0:
                for i in range(len(source_file_t[j])):
                    source_file_t[j][i] = str((truecasing(truecaser, source_file_t[j][i].split(' ')[0]).decode(
                        'utf-8') + " " + (' '.join(source_file_t[j][i].split(' ')[1:]).decode('utf-8'))).encode('utf-8'))
                    print source_file_t[j][i]

    # IF NEITHER
    if not (info['tc'] or info['tok']):
        for j in range(len(source_file_t)):
            if j % 2 == 0:
                for i in range(len(source_file_t[j])):
                    try:
                        source_file_t[j][i] = str(source_file_t[j][i].encode('utf-8'))
                    except NameError:
                        source_file_t[j][i] = str(' '.join(source_file_t[j][i].split('.') + ['.']))

    return source_file_t

def post_processing(detokenizer, trans, info):
    detokenized = ''
    if info['tok']:
        for i in trans:
            splitting = re.split('([\t\n\r\f\v]+)', i)
            for j in range(len(splitting)):
                if j % 2 == 0:
                    try:
                        detokenized_par = detokenizer.detokenize(
                            (splitting[j] + " ").decode('utf-8').split(), return_str=True)
                        detokenized += detokenized_par[0].upper() + detokenized_par[1:] + " "
                    except IndexError:
                        pass
                else:
                    detokenized += splitting[j]
    else:
        for i in trans:
            detokenized_par = i.decode('utf-8') + " "
            detokenized += detokenized_par[0].upper() + detokenized_par[1:]
    print detokenized.replace('@@ ', '').encode('utf-8')
    detokenized = detokenized.replace('@@ ', '').encode('utf-8').strip()
    return detokenized

def parallelized_main(c, tokenizer, detokenizer, truecaser):
    gotthis = c.recv(4096)
    info = json.loads(gotthis, encoding='utf-8')
    source_file_t = pre_processing(tokenizer, truecaser, info)
    try:
        while source_file_t[0][0] != "EOT":
            trans = []
            weights = []
            raw_in = []
            for j in range(len(source_file_t)):
                if j % 2 == 0:
                    for i in source_file_t[j]:
                        temp = nmt.translate([i])[0][:-4].split(' ||| ')
                        # To handle different outputs, origin of difference yet to be determined
                        if len(temp) == 2:
                            trans += [temp[0]]
                            weights += [temp[1]]
                            raw_in += [i]
                        else:
                            trans += [temp[1]]
                            weights += [temp[2]]
                            raw_in += [temp[0]]
                else:
                    trans[-1] += str(source_file_t[j])
            postproced = post_processing(detokenizer, trans, info)
            if info['alignweights']:
                msg = json.dumps({'raw_trans': trans,
                                  'raw_input': raw_in,
                                  'weights': weights,
                                  'final_trans': postproced
                                  }, encoding='utf-8')
            else:
                msg = json.dumps({'raw_trans': trans,
                                  'raw_input': source_file_t[0],
                                  'final_trans': postproced
                                  }, encoding='utf-8')
            c.send(msg)
            gotthis = c.recv(4096)
            try:
                info = json.loads(gotthis, encoding='utf-8')
                source_file_t = pre_processing(tokenizer, truecaser, info)
            except ValueError:
                break
        c.close()
        sys.stderr.write('Done\n')
    except IndexError:
        c.close()
        sys.stderr.write('Bad connecntion made\n')


def listen(c, addr, tokenizer, detokenizer, truecaser):
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
                                     args=(c, tokenizer, detokenizer, truecaser))
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


def main(truecase, sock):
    s = socket.socket()  # Create a socket object
    host = socket.gethostname()  # Get local machine name
    port = sock  # Reserve a port for your service.
    s.bind((host, port))  # Bind to the port #  Now wait for client connection.

    # Initialise truecaser
    with codecs.open(truecase, 'r', encoding='utf-8') as f:
        tc_init = f.read().split('\n')
    truecaser = defaultdict(str)
    for line in tc_init:
        truecaser[line.split(' ')[0].lower()] = line.split(' ')[0]

    # Initialise nltk.moses tokenizer and detokenizer
    tokenizer = moses.MosesTokenizer()
    detokenizer = moses.MosesDetokenizer()

    # Start listening for connections
    while True:
        try:
            s.listen(5)
            print("Waiting for connections and stuff...")
            c, addr = s.accept()
            t = threading.Thread(target=listen,
                                 args=(c, addr, tokenizer, detokenizer, truecaser))
            t.start()
        except KeyboardInterrupt:
            break
    s.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", dest="config")
    parser.add_argument("-e", dest="truecase")
    parser.add_argument("-s", dest="socket", type=int, default=12345)
    args = parser.parse_args()

    ## MODEL LOADED HERE
    nmt.init("-c {}".format(args.config))
    main(args.truecase, args.socket)
