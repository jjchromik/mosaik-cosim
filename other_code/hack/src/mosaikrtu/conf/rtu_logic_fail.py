
################################################################################################################################################
# This is the logic of the PLC. We assume it controls the balance between lines 16 and 16a connecting node a_2 with d_1. It contains a possible failure.
################################################################################################################################################


import random

for  measurements in self.cached_val.values():
    if "sensor" in measurements["dev"]:
        self.to_db(measurements["reg_type"], measurements["index"], measurements["value"][0])
    if "switch" in measurements["dev"]:
        if measurements["place"] == "branch_16":
            if (float(self.cached_val["sensor_1-branch_16"]["value"][0]) > 0.6*self.max_current["branch_16"]) and not self.db("ir", 2):
                self.to_db("ir", 2, 1)
                print("Turning the branch_16a ON, because the current increased above 0.6 of max current.")
            elif (float(self.cached_val["sensor_1-branch_16"]["value"][0]) < 0.3*self.max_current["branch_16"]) and self.db("ir", 2): 
                self.to_db("ir", 2, 0)
                print("Turning the branch_16a OFF, because the current decreased below 0.3 of max current.")
                ###### Faking a failure ######
                if bool(random.getrandbits(1)):
                    self.to_db("ir", 0, 0)
                    print("Turning the branch 16 also OFF to see if this works ")