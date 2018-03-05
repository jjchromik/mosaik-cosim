#!/usr/bin/env python

file = './hello.txt'
text = 'Goodbye TIMMY World!'

fp = open(file, 'w+')
fp.write(text)