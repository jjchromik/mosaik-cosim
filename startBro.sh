#! /bin/bash
export PYTHONPATH=/usr/local/bro/lib/broctl:/Users/chromikjj/Code/mosaik-demo/monitoring/bro-netcontrol-master/

#cd /Users/chromikjj/Code/mosaik-demo/monitoring/bro-netcontrol-master/command-line
#python ./command-line.py --debug
#sleep 10
#/usr/local/bro/bin/bro ./example.bro


cd /Users/chromikjj/Code/mosaik-demo-integrated/monitoring/
#python ./command-line.py --debug
#sleep 10
/usr/local/bro/bin/bro  -i vboxnet0 ./RTU_3.bro
