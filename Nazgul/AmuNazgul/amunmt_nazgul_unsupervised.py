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
import utils
import fastText
import subprocess

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../build/src')
import libamunmt as nmt
from collections import defaultdict
from nltk.tokenize import moses, sent_tokenize

FORMAT = '%(asctime)-15s %(levelname)s %(message)s'
logging.basicConfig(level=logging.DEBUG, format=FORMAT)
LOG = logging.getLogger()


def truecasing(truecaser, word):
    result = truecaser[word.lower()]
    if len(result) > 0:
        return result
    else:
        return word


def pre_processing(tokenizer, truecaser, info, ft_mdl, bpe):
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
    
    #BPE
    if info['tc']:
        for j in range(len(source_file_t)):
            if j % 2 == 0:
                for i in range(len(source_file_t[j])):
                    cmd = "echo " + source_file_t[j][i] + " | python apply_bpe.py -c " + bpe
                    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
                    (out, err) = proc.communicate()
                    source_file_t[j][i] = out[:-1]
                    
    # FASTTEXT
    for j in range(len(source_file_t)):
        if j % 2 == 0:
            for i in range(len(source_file_t[j])):
                x = ft_mdl.predict(unicode(source_file_t[j][i], 'utf-8'))
                source_file_t[j][i] = str(x[0][0].split('_')[-1]).encode('utf-8') + ' ' + source_file_t[j][i]
    return source_file_t



def parallelized_main(c, tokenizer, detokenizer, truecaser, ft_mdl, bpe):
    # print tokenize
    gotthis = c.recv(4096)
    info = json.loads(gotthis, encoding='utf-8')
    source_file_t = pre_processing(tokenizer, truecaser, info, ft_mdl, bpe)
    # print "Finished pre-processing"
    try:
        while source_file_t[0][0] != "EOT":
            detokenized = ''
            trans = []
            weights = []
            raw_in = []
            for j in range(len(source_file_t)):
                if j % 2 == 0:
                    for i in source_file_t[j]:
                        #print nmt.translate([i])[0].split(' |||')
                        #bpe_input = utils.get_bpe_sent(i)
                        
                        #LOG.debug(bpe_input)
                        translated_sent = nmt.translate([i])
                        #is_good = utils.is_good_sentence(translated_sent[0], -5)
                        #LOG.debug(is_good)
                        temp = translated_sent[0].split(' |||')
                        # temp = nmt.translate([i])[0].split(' |||')# hacked for marian[:-4].split(' ||| ')
                        LOG.debug(translated_sent)
                        #for k in nmt.translate([i])[0][:-4].split(' ||| '):
                        #    print k
                        trans += [temp[0]]# hacekd for marian [temp[1]]
                        weights += ['0']
                        # weights += [temp[1]]# hacked atm [temp[2]]
                        raw_in += [i]# hacked for marian [temp[0]]
                else:
                    trans[-1] += str(source_file_t[j])
            if info['tok']:
                for i in trans:
                    splitting = re.split('([\t\n\r\f\v]+)', i)
                    for j in range(len(splitting)):
                        if j % 2 == 0:
                            try:
                                detokenized_par = detokenizer.detokenize((splitting[j] + " ").decode('utf-8').split(), return_str=True)
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
            if info['alignweights']:
                msg = json.dumps({'raw_trans': trans,
                                  'raw_input': raw_in,
                                  'weights': weights,
                                  'final_trans': detokenized.replace('@@ ', '').encode('utf-8').strip()
                                  }, encoding='utf-8')
            else:
                msg = json.dumps({'raw_trans': trans,
                                  'raw_input': source_file_t[0],
                                  'final_trans': detokenized.replace('@@ ', '').encode('utf-8').strip()
                                  }, encoding='utf-8')
            c.send(msg)
            # print(msg)
            LOG.debug(msg)
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


def listen(c, addr, tokenizer, detokenizer, truecaser, ft_mdl, bpe):
    while True:
        try:  # Establish connection with client.
            try:
                print("Got connection from", addr)
                LOG.info("Receiving...")
                fname = c.recv(4096)
            except socket.error:
                c.close()
                LOG.info("Connection closed")
                break
            print fname
            try:
                c.send("okay")
                t = threading.Thread(target=parallelized_main,
                                     args=(c, tokenizer, detokenizer, truecaser, ft_mdl, bpe))
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


def main(truecase, sock, fasttext, bpe):
    s = socket.socket()  # Create a socket object
    host = socket.gethostname()  # Get local machine name
    port = sock  # Reserve a port for your service.
    s.bind(('', port))  # Bind to the port #  Now wait for client connection.

    with codecs.open(truecase, 'r', encoding='utf-8') as f:
        tc_init = f.read().split('\n')

    truecaser = defaultdict(str)
    for line in tc_init:
        truecaser[line.split(' ')[0].lower()] = line.split(' ')[0]
        
    ft_mdl = fastText.load_model(fasttext)

    tokenizer = moses.MosesTokenizer()
    detokenizer = moses.MosesDetokenizer()
    while True:
        try:
            s.listen(5)
            LOG.info("Waiting for connections and stuff...")
            c, addr = s.accept()
            t = threading.Thread(target=listen,
                                 args=(c, addr, tokenizer, detokenizer, truecaser, ft_mdl, bpe))
            t.start()
        except KeyboardInterrupt:
            break
    s.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", dest="config")
    parser.add_argument("-e", dest="truecase")
    parser.add_argument("-s", dest="socket", type=int, default=12345)
    parser.add_argument("-f", dest="fasttext")
    parser.add_argument("-b", dest="bpe")
    args = parser.parse_args()

    ## MODEL LOADED HERE
    # nmt.init("-c {}".format('config.et.en.yml'))
    print("here")
    nmt.init("-c {}".format(args.config))
    print("loaded")
    main(args.truecase, args.socket, args.fasttext, args.bpe)
    # main(True, 'et-truecase.mdl', 12348)
