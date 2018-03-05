# Annhame: doppel leitungen haben die namenskonvention leitung 1: name, leitung 2: namea    
# Annahme: sensor und switch haben gleiche nummer

# print("hr")
# print(self.datablock.store.store['h'].values)

for measurements in self.cached_val.values():
    if "sensor" in measurements["dev"]:
        self.to_db(measurements["reg_type"], measurements["index"], measurements["value"][0])

"""
Check if a sensor at a node/branch is unsafe.
For now we check if voltage, voltage angle and current only change within a certain margin.
If the margin exceeds certain values(adjustable in the worker init), warning values will be increased.
If the warning value exceeds a certain value(adjustable in the worker init), we mark the sensor as untrusted.
All sensor warning values are reduced by a certain value(adjustable in RTU class step method) in every RTU step.
"""
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
    if self.va_mutex: # make sure this function is only run once at a time
        # !!!!!!!!!!!!!!!!!!!!!!!! if you want to disable one of these, transfer the va_mutex to the active methods!!!!!!!!!!!!
        self.check_voltage_angle_equal()
        #self.check_voltage_angle_equal_majority()
        self.check_voltage_angle_difference_adjacent_rtus()
        self.check_voltage_angle_difference()
        self.update_voltage_angle_dict()

# Check if voltage magnitude changes violate the set rules
if self.voltage_magnitude: # check if the voltage magnitude dict is already initialized
    if self.vm_mutex: # make sure this function is only run once at a time
        # !!!!!!!!!!!!!!!!!!!!!!!! if you want to disable one of these, transfer the va_mutex to the active methods!!!!!!!!!!!!
        self.check_voltage_magnitude_equal()
        #self.check_voltage_magnitude_equal_majority()
        self.check_voltage_magnitude_difference()
        self.update_voltage_magnitude_dict()

# Check if current changes violate the set rules
if self.current: # check if the voltage magnitude dict is already initialized
    if self.current_mutex: # make sure this function is only run once at a time
        # !!!!!!!!!!!!!!!!!!!!!!!! if you want to disable one of these, transfer the current_mutex to the active methods!!!!!!!!!!!!
        self.check_current_difference()
        self.update_current_dict()

"""
RTU data will be checked here.
Search for violations of R1, R2 and R4. Collect information needed to check P1(Kirchoff's Law).
"""
if self.physical_data:
    self.check_requierements_and_laws()

"""
Here commands are checked for legitimacy.
"""
if self.commands:
    if self.command_mutex: # make sure this function is only run once at a time
        self.check_commands()

####################################################################################################################################################################################################
# some notes: 

# not implemented:
# what to do if R1 positive? (ask others)
# P2 (TODO: when P_from and P_to readable read them!) Atm P2 is not implementable because I_real is never 0. 
# P4 P is always 0.0 which is nonsense. Therefore it is not implementable atm.

# if communication would be possible:
# Check if a command was created in a RTU step. If yes start a simulation and see if the command leads to a bad state. 
# P3 we have power loss(=> need to know length, resistance, etc.; P_from and P_to belong to 2 different rtus)
# R3 RTUs would need information about the entire grid

# others:
# P5&6 Transformer stuff(therefore not necessary)
####################################################################################################################################################################################################