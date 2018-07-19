@load base/protocols/modbus
@load base/utils/exec
#@load base/frameworks/netcontrol

global voltage_margin = 0.09;

#// TODO: this should be loaded from a configuration file: 
global lines: set[string] = {"l_19", "l_25", "l_24", "l_36"};
global switches: table[string] of bool = {
	["X_19.st"] = T, 
	["X_24.st"] = T, 
	["X_25.st"] = T, 
	["X_36.st"] = T
};
global switches_name: table[count] of string = {
	[0] = "X_19.st", 
	[1] = "X_24.st", 
	[2] = "X_25.st", 
	[3] = "X_36.st"
};
global switches_address: table[string] of count = {
	["X_19.st"] = 0,
	["X_24.st"] = 1,
	["X_25.st"] = 2,
	["X_36.st"] = 3
};
global interlock: table[count] of set[string] = {
	[1] = set("X_19.st", "X_24.st"),
	[2] = set("X_25.st", "X_36.st")
};
global voltage: set[string] = {"B_5.M.V"};
global currents: set[string] = {"L_19.B_5.M.I", "L_24.B_5.M.I", "L_25.B_5.M.I", "L_36.B_5.M.I"};
global sensors_value: table[string] of double = {
	["L_19.B_5.M.I"] = 0.0,
	["L_24.B_5.M.I"] = 0.0,
	["L_25.B_5.M.I"] = 0.0,
	["L_36.B_5.M.I"] = 0.0,
	["B_5.M.V"] = 0.0,
	["T_1.p"] = 0.0,
	["REF.M.V"] = 110000.0,
	["L_1.T_1.M.V"] = 0.0

};
global sensors_name: table[count] of string = {
    [12] = "B_5.M.V",
	[16] = "L_19.B_5.M.I",
	[20] = "L_24.B_5.M.I",
	[24] = "L_25.B_5.M.I",
	[28] = "L_36.B_5.M.I",
	[50] = "T_1.p",
	[54] = "REF.M.V",
	[58] = "L_1.T_1.M.V"
};
global sensors_address: table[string] of count = {
    ["B_5.M.V"] = 12,
	["L_19.B_5.M.I"] = 16,
	["L_24.B_5.M.I"] = 20,
	["L_25.B_5.M.I"] = 24,
	["L_36.B_5.M.I"] = 28,
	["T_1.p"] = 50,
	["REF.M.V"] = 54,
	["L_1.T_1.M.V"] = 58
};
global i_max: table[string] of double = {
	["L_19.B_5.M.I"] = 1.0,
	["L_24.B_5.M.I"] = 1.2,
	["L_25.B_5.M.I"] = 1.2,
	["L_36.B_5.M.I"] = 1.0
};
global v_ref: table[string] of double = {
    ["REF.M.V"] = 110000.0,
    ["L_1.T_1.M.V"] = 10000.0,
    ["B_5.M.V"] = 10000.0
};
global types: table[string, string] of set[count] = {
	["coil", "switches"] = set(0, 1, 2, 3),
	["register", "current"] = set(16, 20, 24, 28),
	["register", "voltage"] = set(12, 54, 58),
	["register", "transformer_tap"] = set(50)
};

global trafo_meters: table[string, string] of string = {
	["V", "P"] = "REF.M.V",
	["V", "S"] = "L_1.T_1.M.V"
};

global trafo_r: table[int] of double = {
	[-1] = 1.0,
	[0]  = 1.05,
	[1]  = 1.1
};

global temp: table[string] of vector of count;


export {
#    const py_threshold = fmt("%s/../../monitoring/thresholds.py", @DIR);
    const py_translate = fmt("%s/../../monitoring/translate.py", @DIR);
}

function current_thresholds() {
    for (c in currents)
    {
        if (sensors_value[c] > i_max[c])
        {
            print fmt("! Current exceeded for sensor %s !", c);
        }
    }
}

function voltage_thresholds() {
    for (v in voltage)
    {
        if ( (sensors_value[v] >= (1+voltage_margin)*v_ref[v]) || (sensors_value[v] <= (1-voltage_margin)*v_ref[v]) )
        {
        	print fmt("LOG;%s;voltage-violation!", current_time());
            #print fmt("! Voltage at sensor %s outside of the allowed bounds!", v);
        }
    }
}

function check_interlocks(address: count, value: bool): bool
{
	#// Always allow if the value turns to true.
	local amt:count = 0;
	for (i in interlock){
		if (switches_name[address] in interlock[i]) {
			#//nr_lines = |interlock[i]|;
			for (sw in interlock[i]){
				if (switches[sw] == T) {++amt;}
			}
		}
	}
	if ( amt >=2 ) return T; #// At least two lines are connected to allow disconnecting one
	else return F;
}


function check_transformer(address: count, value: double): bool  #
{
	local ratio: double = (v_ref["REF.M.V"] / v_ref["L_1.T_1.M.V"])/trafo_r[to_int(fmt("%f", value))];
	if (( sensors_value["REF.M.V"]/ratio > 0.9 * v_ref["L_1.T_1.M.V"] ) && ( sensors_value["REF.M.V"]/ratio < 1.1 * v_ref["L_1.T_1.M.V"] )) {
		return T;
	}
	else {
		print fmt("LOG;%s;BRO-trafo-violation", current_time());
		return F;
	}
}

event bro_init()
{
	print "Initialize model of the system around RTU_3 (bus b_5).";
    print "";
	print "######################################################";
	print "########### Substation on bus b_5 (RTU 3) ############";
	print "######################################################";
	print "";
	print "";
}

event modbus_message(c: connection, headers: ModbusHeaders, is_orig: bool) &priority=10
{
# for TEST
}


###########################################
########### MODBUS WRITE EVENTS ###########
###########################################

event modbus_write_single_coil_request(c: connection, headers: ModbusHeaders, address: count, value: bool)
{
	print fmt("TEST: New Modbus write single coil request: set coil %s to %s.", address, value);
	print fmt("LOG;%s;BRO-command-entry", current_time());

	# Check this only if the value is F; we can always allow to close a switch
	if (value == F) {
		if (check_interlocks(address, value)==T)
			{
			print fmt("LOG;%s;BRO-command-allowed", current_time());
			switches[switches_name[address]] = value; #// put to temp
			}
		else
		{
			if (switches[switches_name[address]] == value)
				{
				print fmt("LOG;%s;BRO-command-repeat", current_time());
				}
			else 
				{
				print fmt("LOG;%s;BRO-command-ALERT", current_time());
				switches[switches_name[address]] = value; #// put to temp
				# TODO: NetControl::drop_address(c$id$orig_h, 60 sec);
				# TODO: NetControl::drop_connection(c$id, 20 sec);
				}
		}

	}
	else { #if true
		# update the switch state 
		switches[switches_name[address]] = value;
	}
}

event modbus_write_single_coil_response(c: connection, headers: ModbusHeaders, address: count, value: bool)
{
	print fmt("LOG;%s;BRO-command-RESPONSE", current_time());
}




##########################################
########### MODBUS READ COILS ############
##########################################

#
# Read the coils and store the local values of the switches.
# Check for interlock status (Needed?)
#

event modbus_read_coils_request(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
{
	temp[fmt("%s-%s", c$id, headers$tid)] = vector(start_address, quantity);
}

event modbus_read_coils_response(c: connection, headers: ModbusHeaders, coils: ModbusCoils)
{
	if ( fmt("%s-%s", c$id, headers$tid) in temp ) {
		# update value with address temp[fmt("%s-%s", connection$id, headers$tid)
		switches[switches_name[temp[fmt("%s-%s", c$id, headers$tid)][0]]] = coils[0];
		delete temp[fmt("%s-%s", c$id, headers$tid)];
		#print switches;
	}
	else
		#// Unknown response! 
		print fmt("LOG;%s;BRO-coil response-UNKNOWN: %s-%s", current_time(), c$id, headers$tid);
}


########################## TODO: -> make overall safety checks together
##### READ REGISTERS ##### TODO: ->  -||-         consistency
##########################

#
# Read registers and update the local values of the readings from current and voltage.
# Check whether the violations on the max current and voltage bounds is not violated.
#

event modbus_read_holding_registers_request(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
{
    # Storing in a local temporary table, to be removed upon response.
	temp[fmt("%s-%s", c$id, headers$tid)] = vector(start_address, quantity);
}

event modbus_read_holding_registers_response(c: connection, headers: ModbusHeaders, registers: ModbusRegisters)
{
# Registers in the response span from 0 : quantity-1
# Assumes only 4 bit registers
    if ( fmt("%s-%s", c$id, headers$tid) in temp ) {
        # Get the actual value of the registers
        local start_address: count;
        local quantity: count;
        start_address = temp[fmt("%s-%s", c$id, headers$tid)][0];
        #print start_address;
        quantity = temp[fmt("%s-%s", c$id, headers$tid)][1];
        local subreg: vector of count;
        local i: count;
        local temp_double: double;
        temp_double = 0;
        i = 0;
        for (r in registers)
            {
            if (i == 3) {
                subreg[i] = registers[r];
                local command = Exec::Command($cmd=fmt("%s %s", py_translate, subreg));
                    when ( local result = Exec::run(command) )
                        {
                        sensors_value[sensors_name[start_address]] = to_double(result$stdout[0][1:-1]);
                        }
                    start_address = start_address + (i+1);
                    i = 0;
                }
            else
                {
                subreg[i] = registers[r];
                i = i+1;
                }
            }
        #print sensors_value;
        if (start_address == 32) {voltage_thresholds(); }
        current_thresholds();
		delete temp[fmt("%s-%s", c$id, headers$tid)];
	}
	else
		#// Unknown response!
		print fmt("LOG;%s;BRO-coil response-UNKNOWN: %s-%s", current_time(), c$id, headers$tid);
}



event modbus_write_multiple_registers_request(c: connection, headers: ModbusHeaders, start_address: count, registers: ModbusRegisters)
{
	# print "    New Modbus write multiple registers request.";
	# Get the actual value of the registers
    local subreg: vector of count;
    local i: count;
    local temp_double: double;
    temp_double = 0;
    i = 0;
    for (r in registers)
        {
        if (i == 3) {
            subreg[i] = registers[r];
            local command = Exec::Command($cmd=fmt("%s %s", py_translate, subreg));
                when ( local result = Exec::run(command) )
                    {
                    temp_double = to_double(result$stdout[0][1:-1]);
                    sensors_value[sensors_name[start_address]] = temp_double;
                    	if (check_transformer(start_address, temp_double)==F) {
	    				print fmt("! Tap position of %s is dangerous for the system !", sensors_name[start_address]);
    					}
                    }
                start_address = start_address + (i+1);
                i = 0;
            }
        else
            {
            subreg[i] = registers[r];
            i = i+1;
            }
        }


}

event modbus_write_multiple_registers_response(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
{
	#print "    New Modbus write multiple registers response.";
}


###############################################
########### MODBUS UNUSED FUNCTIONS ###########
###############################################

#Funcion translating 4 registers into a floating value
#function translate(registers: ModbusRegisters): double  {
#    local command = Exec::Command($cmd=fmt("%s %s", py_translate, registers));
#    when ( local result = Exec::run(command) )
#        {
#        print "This should be printed second";
#        return to_double(result$stdout[0][1:-1]);
#        }
#}




#event NetControl::init()
#	{
#	local debug_plugin = NetControl::create_debug(T);
#	NetControl::activate(debug_plugin, 0);
#	}

#event connection_established(c: connection)
#	{
#	NetControl::drop_connection(c$id, 60 sec);
#	}


event modbus_write_multiple_coils_request(c: connection, headers: ModbusHeaders, start_address: count, coils: ModbusCoils)
{
	print "    New Modbus write multiple coils request.";

}
event modbus_write_multiple_coils_response(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
{
	print "    New Modbus write multiple coils response.";
}


event modbus_write_single_register_request(c: connection, headers: ModbusHeaders, address: count, value: count)
{
	print "    New Modbus write single register request.";

}

event modbus_write_single_register_response(c: connection, headers: ModbusHeaders, address: count, value: count)
{
	print "    New Modbus write single register response.";
}



event modbus_read_write_multiple_registers_request(c: connection, headers: ModbusHeaders, read_start_address: count, read_quantity: count, write_start_address: count, write_registers: ModbusRegisters)
{
	print "    New Modbus read/write multiple registers request.";
}

event modbus_read_write_multiple_registers_response(c: connection, headers: ModbusHeaders, written_registers: ModbusRegisters)
{
	print "    New Modbus read/write multiple registers response.";
}


event modbus_read_discrete_inputs_request(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
{
	print "    New Modbus read discrete inputs request.";
}

event modbus_read_discrete_inputs_response(c: connection, headers: ModbusHeaders, coils: ModbusCoils)
{
	print "    New Modbus read discrete inputs response.";
}

event modbus_read_input_registers_request(c: connection, headers: ModbusHeaders, start_address: count, quantity: count)
{
	print "    New Modbus read input registers request.";
}


event modbus_read_input_registers_response(c: connection, headers: ModbusHeaders, registers: ModbusRegisters)
{
	print "    New Modbus read input registers response.";
}

event bro_done()
{
	print "Done.";
}