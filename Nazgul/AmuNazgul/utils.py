import os
import subprocess
import numpy as np
import math
from io import StringIO

def get_bpe_sent(src_string):
    """Return a sentence that split by BPE units"""
    if os.path.exists("input_file"):
        os.remove("input_file")
    with open("input_file", 'w') as fi:
        fi.write(src_string)
    # input_file = StringIO(unicode(src_string))
    return subprocess.check_output('python ../../subword-nmt/apply_bpe.py -c ../../bpe_codes.all < input_file',
                                     shell=True, stderr=subprocess.STDOUT)


def get_att_weights(res_of_translation):
    """Return attention weights"""
    aliTXT = u''
    lineparts = res_of_translation.split(' ||| ')
    #alignment weights
    weightparts = lineparts[1].split(' ')
    for weightpart in weightparts:
        aliTXT += weightpart.replace(',',' ') + '\n'
    if len(aliTXT) > 0:
        c = StringIO(aliTXT)
        ali = np.loadtxt(c)
        ali = ali.transpose()
        aliTXT = ''
    return ali

def getEnt(ali):
    """copy-paste: https://github.com/M4t1ss/SoftAlignments"""
    """return APin"""
    l = len(ali)
    if l == 0:
        l = 1

    res = 0.0
    for pd in ali:
        norm = sum(pd)
        normPd = [p / norm for p in pd]
        entr = -sum([(p * math.log(p) if p else 0) for p in normPd])
        res -= entr

    return res / l

def getRevEnt(ali, w = 0.1):
    """copy-paste: https://github.com/M4t1ss/SoftAlignments"""
    """return APout"""
    return getEnt(list(zip(*ali)))

def getCP(ali, w = 6):
    """copy-paste: https://github.com/M4t1ss/SoftAlignments"""
    """return CP"""
    l = len(ali)
    if l == 0:
        l = 1

    result = 0.0

    for ali_i in ali:
        s = sum(ali_i)

        pen = 1/ (1 + (abs(1 - s))**w)

        result += math.log(pen)
    return result / l

def compute_exp(x_list, alpha=1):
    return([round(math.pow(math.e, -alpha * math.pow(x, 2)) * 100, 2) for x in x_list])

def is_good_sentence(res_of_translation, threshold):
    raw_att_weights = get_att_weights(res_of_translation)
    if isinstance(raw_att_weights[0], (int,float)):
        src_len = 1
        tgt_len = len(raw_att_weights)
        att_weights = [raw_att_weights[:tgt_len]]
    else:
        src_len = len(raw_att_weights)
        tgt_len = len(raw_att_weights[0])
        att_weights = [l[:tgt_len] for l in raw_att_weights[:src_len]]
    APin = getEnt(att_weights)
    APout = getRevEnt(att_weights)
    CP = getCP(att_weights)
    Total = APin + APout + CP
    # return Total > threshold
    return Total

