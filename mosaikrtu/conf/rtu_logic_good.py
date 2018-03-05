
################################################################################################################################################
# This is the logic of the PLC. We assume it controls the balance between lines 16 and 16a connecting node a_2 with d_1
################################################################################################################################################
# TODO: change in such way that it knows / includes the datatypes
print("What is now seen on the holding register {} ".format(self.db("hr", 2)))

for  measurements in self.cached_val.values():
    if "sensor" in measurements["dev"]:
        self.to_db(measurements["reg_type"], measurements["index"], measurements["value"][0])
    if "switch" in measurements["dev"]:
        if measurements["place"] == "branch_16":
            if (float(self.cached_val["sensor_1-branch_16"]["value"][0]) > 0.6*self.max_current["branch_16"]) and not self.db("co", 2):
                self.to_db("co", 2, 1) # 
                print("Turning the branch_16a ON, because the current increased above 0.6 of max current.")
            elif (float(self.cached_val["sensor_1-branch_16"]["value"][0]) < 0.3*self.max_current["branch_16"]) and (float(self.cached_val["sensor_3-branch_16a"]["value"][0]) < 0.3*self.max_current["branch_16a"]) and self.db("co", 2): 
                self.to_db("co", 2, 0)
                print("Turning the branch_16a OFF, because the current decreased below 0.3 of max current.")
#print("Current branch 16 : {}".format(float(self.cached_val["sensor_1-branch_16"]["value"][0])))
#print("Current branch 16a: {}".format(float(self.cached_val["sensor_3-branch_16a"]["value"][0])))
#print("Current branch 17 : {}".format(float(self.cached_val["sensor_2-branch_17"]["value"][0])))

print("Difference: {}".format(float(self.cached_val["sensor_1-branch_16"]["value"][0]) + float(self.cached_val["sensor_3-branch_16a"]["value"][0]) - float(self.cached_val["sensor_2-branch_17"]["value"][0])))
