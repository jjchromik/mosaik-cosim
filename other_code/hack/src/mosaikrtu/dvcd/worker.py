import threading
import time
import itertools
from numpy import isclose
from mosaikrtu.dvcd.worker_web_client import worker_web_client
from mosaikrtu.dvcd.com_client import com_client


class Worker(threading.Thread):

    """
    Thread holding the Modbus Client, its Datablock, and its Functions.
    """

    def __init__(self, datablock, cache):
        threading.Thread.__init__(self)
        self.cached_val = cache
        self.datablock = datablock

        # adjacent rtus for communication
        self.adj_rtus = []
        self.com_init = False

        self.physical_data = {}
        self.commands = {}
        self.voltage_angle = {}
        self.voltage_magnitude = {}
        self.current = {}
        self.sensor_warning = {}
        self.initialize_sensor_warning_dict()
        self.do_stop = threading.Event()
        self.sensor_eids = []
        self.initialize_rtu_sensor_eid_list()
        self.max_current = {}
        self.initialize_max_currents()

        # Voltage
        self.voltage = 10000
        # per cent offset allowed from Voltage
        self.V_offset = 0.1
        # min per cent trigger for second line
        self.trigger_min_current = 0.3
        # max per cent trigger for second line
        self.trigger_max_current = 0.6

        # absolute tolerance for voltage angle change
        self.atol_voltage_angle = 0.01
        # percentage of absolute change at which a great warning is given for
        # voltage angle
        self.va_great_warning = 0.9
        # percentage of absolute change at which a warning is given for voltage
        # angle
        self.va_warning = 0.8

        # absolute tolerance for adjacent voltage angle change
        self.atol_adj_voltage_angle = 0.01
        # percentage of absolute change at which a great warning is given for
        # adjacent voltage angle
        self.adj_va_great_warning = 0.5
        # percentage of absolute change at which a warning is given for adjacent
        # voltage angle
        self.adj_va_warning = 0.3

        # absolute tolerance for voltage magnitude change
        self.atol_voltage_magnitude = 30
        # percentage of absolute change at which a great warning is given for
        # voltage magnitude
        self.vm_great_warning = 0.8
        # percentage of absolute change at which a  warning is given for
        # voltage magnitude
        self.vm_warning = 0.6

        # absolute tolerance for voltage magnitude change
        self.atol_current = 4
        # percentage of absolute change at which a great warning is given for
        # current
        self.current_great_warning = 0.6
        # percentage of absolute change at which a warning is given for current
        self.current_warning = 0.4

        # if this value is exceeded the sensor is marked as unsafe
        self.max_allowed_warning = 100
        # warning value which is added to the warning value when a great
        # warning occurs
        self.unsafe_warning_value = 1000
        # warning value which is added to the warning value when a great
        # warning occurs
        self.great_warning_value = 10
        # warning value which is added to the warning value when a warning
        # occurs
        self.warning_value = 5

        self.eid = ""
        self.wbclient = None
        self.com_client = None
        self.op_client = None

    def stop(self):
        """
        Signal the client to stop its run-loop.
        """
        self.do_stop.set()
        #print(self.eid + ": Worker given stop signal...")

    def execute_logic(self):
        """
        This method contains the functions that will be executed in every RTU step.
        naming convention for alternative lines: if line 1 is named "branch_1", then the alternative line is named "branch_1a"
        sensors and switches belonging to each other have the same numeration
        """
        for measurements in self.cached_val.values():
            if "sensor" in measurements["dev"]:
                self.to_db(measurements["reg_type"], measurements["index"], measurements["value"][0])

        # Check if a sensor at a node/branch is unsafe.
        # For now we check if voltage, voltage angle and current only change within a certain margin.
        # If the margin exceeds certain values(adjustable in the worker init), warning values will be increased.
        # If the warning value exceeds a certain value(adjustable in the worker init), we mark the sensor as untrusted.
        # All sensor warning values are reduced by a certain value(adjustable in RTU class step method) in every RTU step.
        if not self.voltage_angle: # if the voltage angle dict is empty
            if self.physical_data: # and if we have the data
                self.initialize_voltage_angle_dict()

        if not self.voltage_magnitude: # if the voltage magnitude dict is empty
            if self.physical_data: # and if we have the data
                self.initialize_voltage_magnitude_dict() 

        if not self.current: # if the current dict is empty
            if self.physical_data: # and if we have the data
                self.initialize_current_dict()

        # Check if voltage angle changes violate the set rules
        if self.voltage_angle: # check if the voltage angle dict is already initialized
            self.check_voltage_angle_equal()
            #self.check_voltage_angle_equal_majority()
            self.check_voltage_angle_difference_adjacent_rtus()
            self.check_voltage_angle_difference()

        # Check if voltage magnitude changes violate the set rules
        if self.voltage_magnitude: # check if the voltage magnitude dict is already initialized
            self.check_voltage_magnitude_equal()
            #self.check_voltage_magnitude_equal_majority()
            self.check_voltage_magnitude_difference()

        # Check if current changes violate the set rules
        if self.current: # check if the voltage magnitude dict is already initialized
            self.check_current_difference()

        # RTU data will be checked here.
        # Search for violations of R1, R2 and R4. Collect information needed to check P1(Kirchoff's Law).
        if self.physical_data:
            self.check_requierements_and_laws()

        # Here commands are checked for legitimacy.
        if self.commands:
            self.check_commands()

    def start_webclient(self):
        """
        Starts the webclient to webvis.
        """
        self.webclient = worker_web_client()
        self.webclient.start()

    def highlight(self, target):
        """
        Highlights the given target in webview for visualisation.
        :param target: target to highlight
        """
        self.webclient.highlight(target)

    def start_com_client(self, server):
        """
        Starts the communication client.
        :param server: communication server
        """
        self.com_client = com_client(self.eid, self, server)
        self.com_client.start()

    def send_rq(self, target, rq):
        """
        Sends a request to the communication server.
        Available requests:
            at *branch* -> boolean if rtu has *branch*
            Va -> Va value of the rtu
        :param target: array of target rtus or ["all"]
        :param rq: request string
        :return: result of the request
        """
        if self.com_init == True:
            res = self.com_client.send(target, rq)
            # print(self.eid + " got answer: " + str(res))
            return res
        return "communication not yet initialized"

    def broadcast(self, msg):
        """
        Broadcasts a message to all RTUs.
        If it is an attack warning, it also gets send to the operator GUI.
        :param msg: message to send
        """
        self.com_client.broadcast(msg)
        if self.op_client != None:
            msg = msg.split(" ")
            if msg[0] == "atk":
                self.op_client.send_msg("RTU " + self.eid[0:1] + " detected an attack!")

    def initialize_adj_rtus(self):
        """
        Initializes the adjacent rtu array.
        """
        self.com_init = True
        for branch in self.get_branches():
            rq = "at " + branch
            ans = self.send_rq("all", rq)
            for rtu in ans:
                if ans[rtu] == "True" and rtu not in self.adj_rtus:
                    self.adj_rtus.append(rtu)
        # print(self.eid + ": " + str(self.adj_rtus))

    def set_op_client(self, client):
        """
        Sets the operator communication client to the given client.
        :param client: client to set
        """
        self.op_client = client

    def initialize_sensor_warning_dict(self):
        """
        Initialize a dict to keep track of the error number for each sensor.
        """
        for measurements in self.cached_val.values():
            if "sensor" in measurements["dev"]:
                self.sensor_warning[measurements["dev"]] = 0

    def initialize_max_currents(self):
        """
        Reads max currents from the datablocks and saves them in a dict.
        """
        place = ""
        reg_type = ""
        index = ""
        # Seperate Label from rest of the data in the dictionary
        for label, data in self.cached_val.items():
            # Iterate the tupel
            for key, value in data.items():
                # Check if Tupel is describing max current
                if key == 'dev':
                    if value == 'max':
                        # Search the branchname, reg type and index
                        for key, value in data.items():
                            if key == 'place':
                                place = value
                            if key == 'reg_type':
                                reg_type = value
                            if key == 'index':
                                index = value
                        # get max currents from datablock and save it at the
                        # corresponding branch
                        self.max_current[place] = self.db(reg_type, index)

    def initialize_voltage_angle_dict(self):
        """
        Initialize a dict for all voltage angle values.
        """        
        for eid, data in self.physical_data.items():
            for measurements in self.cached_val.values():
                if eid == measurements["dev"]:  # check if sensor belongs to RTU
                    # Va only at nodes for now
                    if "node" in measurements["place"]:
                        for attr, values in data.items():  # attr = I_real etc.
                            if attr == 'Va':
                                # src = Pypower-0.0-branch6 etc. other
                                # variable = real values of I_real etc.
                                for src, Va in values.items():
                                    self.voltage_angle[eid] = Va

    def initialize_voltage_magnitude_dict(self):
        """
        Initialize a dict for all voltage magnitude values.
        """        
        for eid, data in self.physical_data.items():
            for measurements in self.cached_val.values():
                if eid == measurements["dev"]:  # check if sensor belongs to RTU
                    # Vm only at nodes for now
                    if "node" in measurements["place"]:
                        for attr, values in data.items():  # attr = I_real etc.
                            if attr == 'Vm':
                                # src = Pypower-0.0-branch6 etc. other
                                # variable = real values of I_real etc.
                                for src, Vm in values.items():
                                    self.voltage_magnitude[eid] = Vm

    def initialize_current_dict(self):
        """
        Initialize a dict for all real current values.
        """        
        for eid, data in self.physical_data.items():
            for measurements in self.cached_val.values():
                if eid == measurements["dev"]:  # check if sensor belongs to RTU
                    # I_real only at branches for now
                    if "branch" in measurements["place"]:
                        for attr, values in data.items():  # attr = I_real etc.
                            if attr == 'I_real':
                                # src = Pypower-0.0-branch6 etc. other
                                # variable = real values of I_real etc.
                                for src, I_real in values.items():
                                    self.current[eid] = I_real

    def update_voltage_angle_dict(self):
        """
        Updates the voltage angle value in the voltage angle dict.
        """
        for eid, old_Va in self.voltage_angle.items():
            for alt_eid, data in self.physical_data.items():
                if eid == alt_eid:
                    for attr, values in data.items():  # attr = I_real etc.
                        if attr == 'Va':  # voltage angle read by sensor
                            # src = Pypower-0.0-branch6 etc. other variable =
                            # real values of I_real etc.
                            for src, Va in values.items():
                                # replace the old with the new value
                                self.voltage_angle[eid] = Va

    def update_voltage_magnitude_dict(self):
        """
        Updates the voltage magnitude value in the voltage magnitude dict.
        """
        for eid, old_Vm in self.voltage_magnitude.items():
            for alt_eid, data in self.physical_data.items():
                if eid == alt_eid:
                    for attr, values in data.items():  # attr = I_real etc.
                        if attr == 'Vm':  # voltage magnitude read by sensor
                            # src = Pypower-0.0-branch6 etc. other variable =
                            # real values of I_real etc.
                            for src, Vm in values.items():
                                # replace the old with the new value
                                self.voltage_magnitude[eid] = Vm

    def update_current_dict(self):
        """
        Updates the current value in the current dict.
        """
        for eid, old_I_real in self.current.items():
            for alt_eid, data in self.physical_data.items():
                if eid == alt_eid:
                    for attr, values in data.items():  # attr = I_real etc.
                        if attr == 'I_real':  # current read by sensor
                            # src = Pypower-0.0-branch6 etc. other variable =
                            # real values of I_real etc.
                            for src, I_real in values.items():
                                # replace the old with the new value
                                self.current[eid] = I_real

    def db(self, t, i, c=1):
        """
        Gets values from the datablock.
        :param t: Register type, from; 'di', 'co', 'hr', 'ir'
        :param i: Index of register.
        :param c: Amount of registers to read.
        :return: List of values.
        """
        if c == 1:
            return self.datablock.get(t, i, c)[0]
        return self.datablock.get(t, i, c)

    def to_db(self, t, i, data):
        """
        Sets values in the datablock.
        :param t: Register type, from; 'di', 'co', 'hr', 'ir'
        :param i: Index of register.
        :return: List of values.
        """
        self.datablock.set(t, i, data)

    def reset_trust(self):
        """
        Make every sensor trustable.
        """
        for measurements in self.cached_val.values():
            self.sensor_warning[measurements["dev"]] = 0
            measurements["trusted"] = "True"

    def check_trust(self, eid):
        """
        Method checks if the given sensor is to be trusted.
        :param eid: Sensor to be checked. 
        """
        for measurements in self.cached_val.values():
            if measurements["dev"] == eid:
                if measurements["trusted"] == "True":
                    return True
                else:
                    return False

    def get_branches(self):
        """
        Returns all branches belonging to this RTU
        :return: List containing the branches.
        """
        branches = []
        for measurements in self.cached_val.values():
            if "branch" in measurements["place"] and measurements["place"] not in branches:
                branches.append(measurements["place"])
        return branches

    def get_Va(self):
        """
        Returns the voltage angle read by the sensors of this RTU.
        :return: If not all values are the same a ERROR is returned. The voltage angle value otherwise.
        """
        sensors_valid = self.check_node_sensor_same_Va()
        if not sensors_valid:
            return "ERROR"
        for eid, Va in self.voltage_angle.items():
            if self.check_trust(eid):
                return Va

    def check_node_sensor_same_Va(self):
        """
        Checks if all voltage angle values read by safe sensors are the same.
        :return: True if yes, false otherwise.
        """
        for eid, Va in self.voltage_angle.items():
            if self.check_trust(eid):
                for alt_eid, alt_Va in self.voltage_angle.items():
                    if self.check_trust(alt_eid):
                        if not isclose(Va, alt_Va, atol=0.001):
                            return False
        return True

    def change_sensor_warning_value(self, sensor, value):
        """
        Change values in the sensor warning dict.
        :param sensor: Sensor of which the value is to be changed.
        :param value: Value which will be added to the sensor's value in the dict.
        """
        for key_sensor, key_value in self.sensor_warning.items():
            if sensor == key_sensor:
                self.sensor_warning[key_sensor] = key_value + value

    def check_sensor_warning(self, sensor):
        """
        Check the warning value at given sensor and mark the sensor as unsafe if the value exceeds a certain limit.
        :param sensor: Sensor which's warning value is to be checked.
        """
        for key_sensor, key_value in self.sensor_warning.items():
            if key_sensor == sensor:
                if key_value > self.max_allowed_warning:
                    # search for the sensor(@node and branch) and mark it as
                    # unsafe
                    for measurements in self.cached_val.values():
                        # only necessary if currently marked as safe
                        if measurements["trusted"] == "True":
                            if sensor == measurements["dev"]:
                                measurements["trusted"] = "False"
                                self.warning_value += 5
                                self.great_warning_value += 5
                                self.broadcast("atk " + self.eid)
                                print(
                                    key_sensor + " at " + measurements["place"] + " was marked as untrustable => RTU " + self.eid[0:1] + " warning sensitivity was increased and adjacent RTUs were warned.")
                                # increase warning sensitivity for this RTU and neighbour RTUs

    def check_voltage_angle_equal(self):
        """
        Check if sensors on the same node all have the same voltage angle value.
        """
        sensors_valid = True
        for eid, Va in self.voltage_angle.items():
            # do not check sensors we don't trust
            if self.check_trust(eid):
                for alt_eid, alt_Va in self.voltage_angle.items():
                    if self.check_trust(alt_eid):
                        if not isclose(Va, alt_Va, atol=0.001):
                            sensors_valid = False
                            print("Warning: Voltage angle differs for " +
                                  eid + " and " + alt_eid)
        # if not, at least one of them must be compromised, raise the warning
        # value of all sensors on this node
        if not sensors_valid:
            for eid, Va in self.voltage_angle.items():
                self.change_sensor_warning_value(
                    eid, self.warning_value)  # increase the warning value
                self.check_sensor_warning(eid)

    def check_voltage_angle_equal_majority(self):
        """
        Check if sensors on the same node all have the same voltage angle value. 
        The majority will decide which value is correct. If we have several "majorities" we trust no one.
        """
        va_values = {}
        amount = 0
        single_majority = True
        va_majority = 0
        for eid, Va in self.voltage_angle.items():
            # do not check sensors we don't trust
            if self.check_trust(eid):
                if Va in va_values:
                    va_values[Va] += 1
                else:
                    va_values[Va] = 1
        # if length is not one at least one node has to be wrong
        if len(va_values) != 1:
            print("At least one sensor must have wrong voltage angle values at RTU " + self.eid[0:1])
            # determine the amount of sensors belonging to the majority
            for Va, amounts in va_values.items():
                if amounts > amount:
                    amount = amounts
            # determine the amount of majorities and in case we only have one get the key to valid sensors
            majorities = 0
            for Va, amounts in va_values.items():
                if amounts == amount:
                    majorities += 1
                    va_majority = Va
            if majorities != 1:
                single_majority = False
            # If we have several "majorities" we trust no one.      
            if not single_majority:
                print(("Warning: Several majorities found at RTU " + self.eid[0:1]))
                for eid, Va in self.voltage_angle.items():
                    self.change_sensor_warning_value(
                        eid, self.warning_value)  # increase the warning value
                    self.check_sensor_warning(eid)
            else:
                for eid, Va in self.voltage_angle.items():
                    # check if current sensor is part of the majority
                    if Va != va_majority:               
                        self.change_sensor_warning_value(
                            eid, self.unsafe_warning_value)  # increase the warning value
                        print(("Unsafe: Sensor value differs for voltage angle from the other sensors at " + eid))
                        self.check_sensor_warning(eid)


    def check_voltage_angle_difference_adjacent_rtus(self):
        """
        Check if voltage angle difference between adjacent RTUs.
        """
        #maximum = 0
        # check if the voltage angle difference between adjacent nodes is not too big
        adj_Va_values = self.send_rq(self.adj_rtus, "Va")
        for adj_rtu, adj_Va in adj_Va_values.items():
            if str(adj_Va) not in "None":
                if str(adj_Va) == "ERROR":
                    print("ERROR: Cannot check voltage angle difference between RTU " + self.eid[0:1] + " and RTU " + adj_rtu[0:1] + " as RTU " + adj_rtu[0:1] + "'s values are not reliable.")
                else:
                    for eid, Va in self.voltage_angle.items():
                        # if adjacent and new value are not close enough
                        if not isclose(float(adj_Va), Va, atol=self.atol_adj_voltage_angle):
                            self.change_sensor_warning_value(
                                eid, self.unsafe_warning_value)
                            print("Unsafe: Voltage angle difference more than " +
                                  str(self.atol_adj_voltage_angle) + " between " + eid  + " and " + adj_rtu)
                            self.check_sensor_warning(eid)
                        # if adjacent and new value are not close enough
                        # even when giving leeway
                        elif not isclose(float(adj_Va), Va, atol=self.atol_adj_voltage_angle * self.adj_va_great_warning):
                            self.change_sensor_warning_value(
                                eid, self.great_warning_value)  # increase the warning value
                            print("Great warning: Voltage angle difference more than " + str(
                                self.atol_adj_voltage_angle * self.adj_va_great_warning) + " between " + eid  + " and " + adj_rtu)
                            self.check_sensor_warning(eid)
                        else:
                            # if adjacent and new value are not close enough
                            # even when giving more leeway
                            if not isclose(float(adj_Va), Va, atol=self.atol_adj_voltage_angle * self.adj_va_warning):
                                self.change_sensor_warning_value(
                                    eid, self.warning_value)  # increase the warning value
                                print("Warning: Voltage angle difference more than " + str(
                                    self.atol_adj_voltage_angle * self.adj_va_warning) + " between " + eid  + " and " + adj_rtu)
                                self.check_sensor_warning(eid)

    def check_voltage_angle_difference(self):
        """
        Checks change of voltage angle read by sensors. 
        """
        # get a sensors new data by searching for new physical_data from the
        # sensor
        for eid, old_Va in self.voltage_angle.items():
            for alt_eid, data in self.physical_data.items():
                if eid == alt_eid:
                    for attr, values in data.items():  # attr = I_real etc.
                        if attr == 'Va':  # voltage angle read by sensor
                            # src = Pypower-0.0-branch6 etc. other variable =
                            # real values of I_real etc.
                            for src, Va in values.items():
                                # if old and new value are not close enough
                                if not isclose(Va, old_Va, atol=self.atol_voltage_angle):
                                    self.change_sensor_warning_value(
                                        eid, self.unsafe_warning_value)
                                    print("Unsafe: Voltage angle changed more than " +
                                          str(self.atol_voltage_angle) + " at " + eid)
                                    self.check_sensor_warning(eid)
                                # if old and new value are not close enough
                                # even when giving leeway
                                elif not isclose(Va, old_Va, atol=self.atol_voltage_angle * self.va_great_warning):
                                    self.change_sensor_warning_value(
                                        eid, self.great_warning_value)  # increase the warning value
                                    print("Great warning: Voltage angle changed more than " + str(
                                        self.atol_voltage_angle * self.va_great_warning) + " at " + eid)
                                    self.check_sensor_warning(eid)
                                else:
                                    # if old and new value are not close enough
                                    # even when giving more leeway
                                    if not isclose(Va, old_Va, atol=self.atol_voltage_angle * self.va_warning):
                                        self.change_sensor_warning_value(
                                            eid, self.warning_value)  # increase the warning value
                                        print("Warning: Voltage angle changed more than " + str(
                                            self.atol_voltage_angle * self.va_warning) + " at " + eid)
                                        self.check_sensor_warning(eid)

    def check_voltage_magnitude_equal(self):
        """
        Checks if all sensors have the same value as all sensors are at the same node.
        """
        # check if sensors all have the same voltage magnitude value
        sensors_valid = True
        for eid, Vm in self.voltage_magnitude.items():
            if self.check_trust(eid):
                for alt_eid, alt_Vm in self.voltage_magnitude.items():
                    if self.check_trust(alt_eid):
                        if Vm != alt_Vm:
                            sensors_valid = False
                            print("Warning: Voltage magnitude differs for " +
                                  eid + " and " + alt_eid)
        # if not, at least one of them must be compromised, raise the warning
        # value of all sensors on this node
        if not sensors_valid:
            for eid, Vm in self.voltage_magnitude.items():
                self.change_sensor_warning_value(
                    eid, self.warning_value)  # increase the warning value
                self.check_sensor_warning(eid)

    def check_voltage_magnitude_equal_majority(self):
        """
        Check if sensors on the same node all have the same voltage magnitude value. 
        The majority will decide which value is correct. If we have several "majorities" we trust no one.
        """
        vm_values = {}
        amount = 0
        single_majority = True
        vm_majority = 0
        for eid, Vm in self.voltage_magnitude.items():
            # do not check sensors we don't trust
            if self.check_trust(eid):
                if Vm in vm_values:
                    vm_values[Vm] += 1
                else:
                    vm_values[Vm] = 1
        # if length is not one at least one node has to be wrong
        if len(vm_values) != 1:
            print("At least one sensor must have wrong voltage magnitude values at RTU " + self.eid[0:1])
            # determine the amount of sensors belonging to the majority
            for Vm, amounts in vm_values.items():
                if amounts > amount:
                    amount = amounts
            # determine the amount of majorities and in case we only have one get the key to valid sensors
            majorities = 0
            for Vm, amounts in vm_values.items():
                if amounts == amount:
                    majorities += 1
                    vm_majority = Vm
            if majorities != 1:
                single_majority = False
            # If we have several "majorities" we trust no one.      
            if not single_majority:
                print(("Warning: Several majorities found at RTU " + self.eid[0:1]))
                for eid, Vm in self.voltage_magnitude.items():
                    self.change_sensor_warning_value(
                        eid, self.warning_value)  # increase the warning value
                    self.check_sensor_warning(eid)
            else:
                for eid, Vm in self.voltage_magnitude.items():
                    # check if current sensor is part of the majority
                    if Vm != vm_majority:               
                        self.change_sensor_warning_value(
                            eid, self.unsafe_warning_value)  # increase the warning value
                        print(("Unsafe: Sensor value differs for voltage magnitude from the other sensors at " + eid))
                        self.check_sensor_warning(eid)

    def check_voltage_magnitude_difference(self):
        """
        Checks change of voltage magnitude read by sensors.
        """
        # get a sensors new data by searching for new physical_data from the
        # sensor
        for eid, old_Vm in self.voltage_magnitude.items():
            for alt_eid, data in self.physical_data.items():
                if eid == alt_eid:
                    for attr, values in data.items():  # attr = I_real etc.
                        if attr == 'Vm':  # voltage magnitude read by sensor
                            # src = Pypower-0.0-branch6 etc. other variable =
                            # real values of I_real etc.
                            for src, Vm in values.items():
                                # if old and new value are not close enough
                                if not isclose(Vm, old_Vm, atol=self.atol_voltage_magnitude):
                                    self.change_sensor_warning_value(
                                        eid, self.unsafe_warning_value)
                                    print("Unsafe: Voltage magnitude changed more than " +
                                          str(self.atol_voltage_magnitude) + " at " + eid)
                                    self.check_sensor_warning(eid)
                                # if old and new value are not close enough
                                # even when giving leeway
                                elif not isclose(Vm, old_Vm, atol=self.atol_voltage_magnitude * self.vm_great_warning):
                                    self.change_sensor_warning_value(
                                        eid, self.great_warning_value)  # increase the warning value
                                    print("Great warning: Voltage magnitude changed more than " + str(
                                        self.atol_voltage_magnitude * self.vm_great_warning) + " at " + eid)
                                    self.check_sensor_warning(eid)
                                else:
                                    # if old and new value are not close enough
                                    # even when giving more leeway
                                    if not isclose(Vm, old_Vm, atol=self.atol_voltage_magnitude * self.vm_warning):
                                        self.change_sensor_warning_value(
                                            eid, self.warning_value)  # increase the warning value
                                        print("Warning: Voltage magnitude changed more than " + str(
                                            self.atol_voltage_magnitude * self.vm_warning) + " at " + eid)
                                        self.check_sensor_warning(eid)

    def check_current_difference(self):
        """
        Checks if change of current read by sensor is too big.
        """
        # get a sensors new data by searching for new physical_data from the
        # sensor
        for eid, old_I_real in self.current.items():
            for alt_eid, data in self.physical_data.items():
                if eid == alt_eid:
                    for attr, values in data.items():  # attr = I_real etc.
                        if attr == 'I_real':  # current read by sensor
                            # src = Pypower-0.0-branch6 etc. other variable =
                            # real values of I_real etc.
                            for src, I_real in values.items():
                                # if old and new value are not close enough
                                if not isclose(I_real, old_I_real, atol=self.atol_current):
                                    self.change_sensor_warning_value(
                                        eid, self.unsafe_warning_value)
                                    print("Unsafe: Current changed more than " +
                                          str(self.atol_current) + " at " + eid)
                                    self.check_sensor_warning(eid)
                                # if old and new value are not close enough
                                # even when giving leeway
                                elif not isclose(I_real, old_I_real, atol=self.atol_current * self.current_great_warning):
                                    self.change_sensor_warning_value(
                                        eid, self.great_warning_value)  # increase the warning value
                                    print("Great warning: Current changed more than " + str(
                                        self.atol_current * self.current_great_warning) + " at " + eid)
                                    self.check_sensor_warning(eid)
                                else:
                                    # if old and new value are not close enough
                                    # even when giving more leeway
                                    if not isclose(I_real, old_I_real, atol=self.atol_current * self.current_warning):
                                        self.change_sensor_warning_value(
                                            eid, self.warning_value)  # increase the warning value
                                        print("Warning: Current changed more than " + str(
                                            self.atol_current * self.current_warning) + " at " + eid)
                                        self.check_sensor_warning(eid)

    def check_requierements_and_laws(self):
        all_sensors_trustable = True
        bus_data = {}  # dictionary to map all I_real values of branches connected to a node
        for eid, data in self.physical_data.items():
            for measurements in self.cached_val.values():   
                if eid in measurements["dev"]: # check if sensor belongs to RTU
                    if measurements["trusted"] == "True": # only do the rest if we trust the sensor
                        current_node = None
                        for node in data['Vm']:
                            current_node = node
                            if node not in bus_data:
                                bus_data[node] = {}
                        for attr, values in data.items(): #attr = I_real etc.
                            if attr == 'Vm': # voltage magnitude of a node
                                for src, Vm in values.items(): #src = Pypower-0.0-branch6 etc. other variable = real values of I_real etc.
                                    #R1
                                    if "node" in measurements["place"] and (Vm < (self.voltage * (1 - self.V_offset))) or (Vm > (self.voltage * (1 + self.V_offset))):
                                        self.change_sensor_warning_value(
                                            measurements["dev"], self.warning_value)  # increase the warning value
                                        print("Warning: " + measurements["dev"] + "-" + measurements["place"] + " with " + str(Vm) + " Vm out of bound.")
                                        self.check_sensor_warning(measurements["dev"])
                            if attr == 'I_real': # current of a branch
                                for src, I_real in values.items():
                                    if src not in bus_data[current_node]:
                                        bus_data[current_node][src] = I_real
                                        #print(src, I_real)
                                    for branch in self.cached_val.values(): # search for switch belonging to this sensors branch
                                        if ("switch" in branch["dev"]) and (branch["place"] == src[12:]): 
                                            #R4
                                            # check for second branch with naming convention
                                            secbranch = None
                                            for alt_branch in self.cached_val.values():
                                                if "switch" in alt_branch["dev"] and alt_branch["place"] == branch["place"] + "a":
                                                    secbranch = alt_branch
                                                    break
                                            if secbranch:
                                                if (I_real > self.trigger_max_current * self.max_current[branch["place"]]) and \
                                                (I_real < self.max_current[secbranch["place"]]) and not self.db("hr", secbranch["index"]): # 2nd branch needed and not already open and not already over max_current
                                                    self.to_db("hr", secbranch["index"], 1) # the branch will be opened in the next step
                                                    print("Turning the " + secbranch["place"] + " ON, because the current on " + \
                                                    branch["place"] + " increased above " + str(self.trigger_max_current) + " of max current.")
                                                    self.highlight(secbranch["place"])
                                                elif (I_real < self.trigger_min_current * self.max_current[branch["place"]]) and \
                                                self.db("hr", secbranch["index"]):
                                                    for alt_eid, alt_data in self.physical_data.items(): # search for I_real of secbranch
                                                        if alt_eid == measurements["dev"]:
                                                            for alt_attr, alt_values in alt_data.items():
                                                                if alt_attr == 'I_real':
                                                                    for alt_src, alt_I_real in alt_values.items():
                                                                        if secbranch["place"] == alt_src[12:] + "a":
                                                                            if alt_I_real < self.trigger_min_current * self.max_current[secbranch["place"]]:
                                                                                self.to_db("hr", secbranch["index"], 0) # the branch will be closed in the next step
                                                                                print("Turning the " + secbranch["place"] + \
                                                                                " OFF, because the current on " + secbranch["place"] + " and " + \
                                                                                branch["place"] + " decreased below " + str(self.trigger_min_current) + \
                                                                                " of max current.")
                                                                                self.highlight(secbranch["place"])
                                            #R2
                                            if (I_real > self.max_current[branch["place"]]) and self.db("hr", branch["index"]): # if current over the allowed value and switch is still on?
                                                print(branch["place"] + " exceeded power limit of " + \
                                                str(self.max_current[branch["place"]]) + "A.")
                                                self.to_db("hr", branch["index"], 0) # the branch will be closed in the next step
                                                print(branch["place"] + " was closed.")
                                                self.highlight(branch["place"])

                                            break
                    # if one of the sensors is untrusted we cannot correctly check Kirchhoff's law
                    else:
                        all_sensors_trustable = False

        if all_sensors_trustable:
            # P1: Kirchoff's law
            null_sum = False
            node = None
            bus_currents = []
            max_numb_branches = 0
            sign_list = []

            #WORKAROUND: find the bus with the most collected values - this this the bus we're looking at
            for bus, currents in bus_data.items():
                node_branch_numb = len(currents)
                if node_branch_numb > max_numb_branches:
                    node = bus
                    max_numb_branches = node_branch_numb

            #collect all currents for the bus we're looking at in a list
            if node in bus_data:
                for attr, value in bus_data[node].items():
                    bus_currents.append(value)

            for i in range(max_numb_branches):
                sign_list.append(i)

            #get all sign combinations for the values in our currents
            sign_list = list(powerset(sign_list))

            """
            test for all sign combinations of our currents if there is a null-sum.
            If this is the case Kirchoff's law is not violated. If there is no such sum, Kirchoff's law was violated and the
            operator gets a notification.
            """

            for sign_tuple in sign_list:
                sum = 0
                for j in range(max_numb_branches):
                    if j in sign_tuple: # j-th element is marked as "signed"
                        sum -= bus_currents[j]
                    else:
                        sum += bus_currents[j]
                if isclose(sum, 0, atol=1):
                    null_sum = True
                    break

            if not null_sum:
                print("Kirchoff's law is violated at {}.".format(node.split("-")[2]))
                # We must assume every sensor at the node could be suspicious.
                for eid in self.sensor_eids:
                    self.change_sensor_warning_value(
                        eid, self.great_warning_value)  # increase the warning value
                    print("Great Warning: " + eid + " is suspicious as it's node violates Kirchoff's law.")
                    self.check_sensor_warning(eid)


    def initialize_rtu_sensor_eid_list(self):
        """
        This method gets all sensor names of sensors belonging to this RTU and stores them in a list.
        """
        for measurements in self.cached_val.values():
            if "sensor" in measurements["dev"]:
                if "node" in measurements["place"]:
                    self.sensor_eids.append(measurements["dev"])


    def check_commands(self):
        """
        This function checks if commands are valid.
        Currently if neither R2 nor R4 are violated the command will be reversed.
        """
        for rtu, topologies in self.commands.items():  # unpack commands
            for topology, switchstates in topologies.items():
                for switchstate, switch in switchstates.items():
                    for place, switch_status in switch.items():
                        for measurements in self.cached_val.values():  # search for branch data
                            if place == measurements["place"]:
                                for eid, data in self.physical_data.items():
                                    # check if sensor belongs to RTU
                                    if eid in measurements["dev"]:
                                        # only do the rest if we trust the
                                        # sensor
                                        if measurements["trusted"] == "True":
                                            for attr, values in data.items():  # attr = I_real etc.
                                                if attr == 'I_real':  # voltage of a node
                                                    for src, I_real in values.items():
                                                        for branch in self.cached_val.values():  # search for switch belonging to this sensors branch
                                                            if ("switch" in branch["dev"]) and (branch["place"] == src[12:]):
                                                                # branches are only turned on/off by R2 and R4 
                                                                # => check if R2 and R4 are really violated if currently checking a main branch
                                                                if place[-1:] != "a":
                                                                    if switch_status == False:  # main branch will be turned off
                                                                        # R2 if the current is actually under the allowed value but the branch is turned off
                                                                        if (I_real < self.max_current[branch["place"]]) and (not self.db("hr", branch["index"])):
                                                                            print(
                                                                                branch["dev"] + "-" + branch["place"] + " was incorrectly turned off.")
                                                                            # the reverse command will be executed in the next step
                                                                            self.to_db("hr", branch["index"], 1)
                                                                            print(branch["place"] + " was opened.")
                                                                            self.highlight(branch["place"])
                                                                else:  # checking an alternate branch
                                                                    # R4
                                                                    mainbranch = None  # search for the main branch belonging to this alternative branch
                                                                    for alt_branch in self.cached_val.values():
                                                                        if "switch" in alt_branch["dev"] and alt_branch["place"] == place[:-1]:
                                                                            mainbranch = alt_branch
                                                                            break
                                                                        if mainbranch:  # should exist else topology is wrong
                                                                            for main_eid, main_data in self.physical_data.items():  # search for main branch data
                                                                                # check if sensor belongs to RTU
                                                                                if main_eid in mainbranch["dev"]:
                                                                                    for main_attr, main_values in data.items():  # attr = I_real etc.
                                                                                        if main_attr == 'I_real':  # voltage of a node
                                                                                            for main_src, main_I_real in values.items():
                                                                                                if switch_status == True:  # alternative branch will be turned on
                                                                                                    # if alternative branch not needed but turned on
                                                                                                    if (main_I_real < self.trigger_max_current * self.max_current[mainbranch["place"]]) and (self.db("hr", branch["index"])):
                                                                                                        print(branch["dev"] + "-" + branch["place"] + " was incorrectly turned on.")
                                                                                                        # the alternative branch will be closed in the next step
                                                                                                        self.to_db("hr", branch["index"], 0)
                                                                                                        print(branch["place"] + " was closed.")
                                                                                                        self.highlight(branch["place"])
                                                                                                else:  # alternative branch will be turned off
                                                                                                    if  (main_I_real < self.trigger_min_current * self.max_current[mainbranch["place"]]) \
                                                                                                            and (not (I_real > self.max_current[branch["place"]])) and (not self.db("hr", branch["index"])):  # if alternative branch needed(R4) and alternative branch current not exceeding limit(R2) and branch not already turned off
                                                                                                        print(branch["dev"] + "-" + branch["place"] + " was incorrectly turned off.")
                                                                                                        # the alternative branch will be opened in the next step
                                                                                                        self.to_db("hr", branch["index"], 1)
                                                                                                        print(branch["place"] + " was opened.")
                                                                                                        self.highlight(branch["place"])
                                                                break

    @staticmethod
    def to_float(a, b, c, d):
        import struct
        return struct.unpack("f", "".join(chr(int(i)) for i in (a, b, c, d)))[0]

    @staticmethod
    def from_float(a):
        import struct
        return struct.pack("f", a)


def powerset(iterable):
    "powerset([1,2,3]) --> () (1,) (2,) (3,) (1,2) (1,3) (2,3) (1,2,3)"
    s = list(iterable)
    return itertools.chain.from_iterable(itertools.combinations(s, r) for r in range(len(s) + 1))
