# Nazgul
Neural translation service built on top of Marian (formerly known as AmuNMT). Marcin Junczys-Dowmunt, Tomasz Dwojak, Hieu Hoang (2016). Is Neural Machine Translation Ready for Deployment? A Case Study on 30 Translation Directions (https://arxiv.org/abs/1610.01108)

We use the following AmuNMT clone to produce attention info: https://github.com/barvins/amunmt

## Dependencies

 * NLTK and stuff, wrtie commands here

## How to run
 * Download and compile AmuNMT according to instructions from https://github.com/barvins/amunmt
 * To run the nazgul server (inside build directory):
 
    make python

#TODO LIST:

Add link to Sauron 

Add example config file that we use

Explain different flags and how to use them (tokenize, truecase, etc.)

Add example input commands and (maybe?) example output

Explain what input data to use

Explain how the service works?
