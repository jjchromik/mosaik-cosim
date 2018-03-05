# Group: Multiple RTUs
Simulating a power grid with multiple RTUs defending attacks.

## 0. Dependencies
The following packages must be installed via **pip**:
- virtualenv
- simpy
- simpy.io
- pillow

**Mosaik** needs to be installed as well (see https://mosaik.offis.de/install/) and inside of the mosaik environment following packages are needed:
- pymodbus3
    - make sure devicy.py line 221 looks like this: https://github.com/uzumaxy/pymodbus3/blob/master/pymodbus3/device.py#L221

## 1. Simulation
You can start the simulation by running start_simulation.bat, if this folder is in the same dir as the mosaik sourcecode.

The web visualisation is available at **localhost:8000**.

Executing start_hacker_tools.bat, runs the hacker tools cmd (needs the simulation to run).

## 2. Hacker Tools Script Interpreter
Provides an Interpreter so attacks can be run automatically.

### 2.1 Hacker Tools Function
Parameters are divided by comma.
- **listservers** [*True/False*] : **_ht_array_**
- **connect** *port*
- **listbranches** [*True/False*] : **_ht_array_**
- **getstate** *branch***,** [*True/False*] : **_dict_**
- **setswitch** *branch***,** *value*
- **setsensor** *branch***,** *value*
- **setmaxcurrent** *branch***,** *value*

### 2.2 General Functions
- **if** ... *else* ... **ifEnd**
- **for** *var* **in** *start* **to** *end* ... **forEnd**
- **for** *var* **in** *array* ... **forEnd**
- **set** *var* *value*
- **get** *ht_array* : **_array_**
- **get** *value name* **of** *dict* : **_value_**
- **random** *start* *end* : **_value_**
- **random** *array* : **_element_**
- **len** *array* : **_value_**
- **wait** *value*
- **arithmetic**: +, -, *, /, %
- **comparison**: ==, >, <, >=, <=, !=
- **logic**: and, or

### 2.3 Known Bugs and Issues
- logic functions cannot be used with brackets, they are computed from left to right
- interpreter is not completely errorsafe when wrong syntax is used

### 2.4 TODO
- ~~at the moment only integer values are supported, extending to floats would be nice to have~~