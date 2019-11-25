Please be aware that some of the used libraries contain some security issues. I will work on addressing them in my spare time, however, I don't promise when this will be done! 

# Framework for locally implemented model-based traffic monitoring implementing Mosaik co-simulation

On high level, the framework consists of the simulated power grid, simulated controller(s) (RTUs), SCADA server and the monitoring tool implementing Bro. 

To start the system you have to:

1. Install Mosaik using the guidelines provided [here](http://mosaik.readthedocs.io/en/latest/installation.html). **Mosaik runs the simulated power grid and starts the simulated RTUs.**
2. Install Bro using the guidelines provided [here](https://www.bro.org/sphinx/install/install.html). **Bro is the monitoring tool.**
3. Create a VM for your SCADA server. Currently we assume the SCADA server operates on interface `vboxnet0`. This is relevant to know in order to set up the monitoring tool. **This serves as the SCADA server.**
4. `startMosaik.sh` is a bash script that activates the virtualenv of Mosaik and starts the GUI for the topology loader. You can specify which topology you want to use. 
5. `startBro.sh` is a bash script that runs the monitoring tool and listens on interface `vboxnet0` with policies from `monitoring/RTU_3.bro`

The framework consists of Mosaik simulators (directories beginning with mosaik*), the data with topologies (data), the data for monitoring (monitoring), and parts that enable choosing the topology (topology loader).

When installing pymodbus3 library, use: https://github.com/jjchromik/pymodbus3 - it has got two changes than the original github, and they otherwise result in error in the project.
