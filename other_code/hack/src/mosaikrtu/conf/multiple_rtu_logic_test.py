
################################################################################################################################################
# This is the logic of the PLC. We assume it controls the balance between lines 16 and 16a connecting node a_2 with d_1
################################################################################################################################################

for measurements in self.cached_val.values(): # measurments looks like this {'dev': 'sensor_2', 'value': [0], 'place': 'branch_17', 'reg_type': 'co', 'index': 3, 'alternative': 'false'}
    #print(measurements)
    if "sensor" in measurements["dev"]:
        self.to_db(measurements["reg_type"], measurements["index"], measurements["value"][0])
    if "switch" in measurements["dev"]:
        if "true" in measurements["alternative"]:
            sensor = "sensor_"+measurements["dev"][7:] # sensor name without branch: "sensor_1"(this is why switch=sensor numeration, could be stored in label as well)
            branch = measurements["place"] # branch where the switch and sensor are located: "branch_16"
            sensor_label = sensor+"-"+branch # label for sensor belonging to switch: "sensor_1-branch16"
            alternative_branch = branch+"a" # alternative branch name: "branch_16a"
            index, alternative_sensor = measurements["alternative"][4:].split("s") # true2s3 cut to "2" and "3"
            index = int(index) # needs to be int for db function
            alternative_sensor_label = "sensor_"+alternative_sensor+"-"+alternative_branch # "sensor_3-branch_16a"
            if (float(self.cached_val[sensor_label]["value"][0]) > 0.6*self.max_current[branch]) and not self.db("hr", index):
                self.to_db("hr", index, 1)
                print("Turning the "+alternative_branch+" ON, because the current increased above 0.6 of max current.")
            elif (float(self.cached_val[sensor_label]["value"][0]) < 0.3*self.max_current[branch]) and (float(self.cached_val[alternative_sensor_label]["value"][0]) < 0.3*self.max_current[alternative_branch]) and self.db("hr", index): 
                self.to_db("hr", index, 0)
                print("Turning the "+alternative_branch+" OFF, because the current decreased below 0.3 of max current.")
        #if measurements["place"] == "branch_13":
         #   if (float(self.cached_val["sensor_4-branch_13"]["value"][0]) > 0.6*self.max_current["branch_13"]) and not self.db("hr", 8):
          #      self.to_db("hr", 8, 1)
           #     print("Turning the branch_13a ON, because the current increased above 0.6 of max current.")
            #elif (float(self.cached_val["sensor_4-branch_13"]["value"][0]) < 0.3*self.max_current["branch_13"]) and (float(self.cached_val["sensor_6-branch_13a"]["value"][0]) < 0.3*self.max_current["branch_13a"]) and self.db("hr", 8): 
             #   self.to_db("hr", 8, 0)
              #  print("Turning the branch_13a OFF, because the current decreased below 0.3 of max current.")
