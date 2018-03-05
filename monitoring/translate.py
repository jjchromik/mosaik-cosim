#!/usr/bin/env python3
import sys
from struct import pack, unpack
import re

i=1
result=[]
reg_float=[]


for number in sys.argv[1:]:
    number= re.sub("\D", "", number)
    if i%4!=0:
        reg_float.append(int(number))
    else:
        reg_float.append(int(number))
        reg_float = pack(">HHHH", reg_float[0], reg_float[1], reg_float[2], reg_float[3])
        result.append(unpack(">d", reg_float)[0])
        reg_float=[]
    i=i+1
print(format(result))