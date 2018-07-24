# SCADA server and attack source

SCADA server is a simple PyModbus3 client (`SCADA_server.py`) that polls (every 5 seconds) for the values of the controlled currents and voltages. It can be run on a VM and requires pymodbus3 to work. 
When installing pymodbus3 library, use: https://github.com/jjchromik/pymodbus3 - it has got two changes than the original github, and they otherwise result in error in the project.

The `attack_trafo.py` contains attack scenario example on a transformer. It changes the switch position several times including a change making it reach too high voltage. 