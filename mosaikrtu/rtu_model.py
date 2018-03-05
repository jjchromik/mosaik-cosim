# rtu_model.py
# author: Justyna Chromik

"""
This module contains the RTU model with sensors and switches. 

"""
import xml.dom.minidom
from mosaikrtu.dvcd.data import DataBlock
from mosaikrtu.dvcd.server import Server
from mosaikrtu.dvcd.worker import Worker
import struct

import socket


def create_datablock(conf): # changes : to include the datatype of the data.
    # TODO: add a check on the configuration file that if a register is of a certain datatype then it may or may not
    # have certain length (the addresses of the consecutive registers have to be checked)
    """
    Create a Modbus datablock holding the registers described in the XML config file.
    :param conf: Dictionary holding configuration values. See: load_rtu function
    :return: Modbus datablock object that locks when reading or writing.
    """
    datablock = DataBlock()
    regs = conf["registers"]
    for reg_label in regs:
        ty, addr, datatype, value = regs[reg_label]
        if datatype == 'bool':
            if value == "True" or value == 1 or value == 'T':
                value = bool(True)
            elif value == "False" or value == 0 or value == 'F':
                value = bool(False)
            datablock.set(ty, addr, value)
        elif datatype == '8bit_uint':
            continue
        elif datatype == '16bit_uint':
            continue
        elif datatype == '32bit_uint':
            continue
        elif datatype == '64bit_uint':
            continue
        elif datatype == '8bit_int':
            continue
        elif datatype == '16bit_int':
            value = struct.unpack('>H', struct.pack('>h', int(value)))
            datablock.set(ty, addr, value)
        elif datatype == '32bit_int':
            continue
        elif datatype == '64bit_int':
            continue
        elif datatype== '32bit_float':
            datablock.set(ty, addr , float(value), datatype)
            #for i in range(1):
            #    datablock.set(ty, addr+i, struct.unpack('>HH', struct.pack('>f', float(value)))[i])
        elif datatype== '64bit_float':
            datablock.set(ty, addr , float(value), datatype)
            #for i in range(3):
            #    datablock.set(ty, addr + i, struct.unpack('>HHHH', struct.pack('>d', float(value)))[i])
        elif datatype == 'string':
            continue

    return datablock


def create_server(conf, datablock):
    """
    Create a Server with supplied datablock and configured identity.
    :param conf: Dictionary holding configuration values. See: tools/loader.py
    :param datablock: Modbus datablock object.
    :return: Modbus Server object.
    """
    #global args
    server = Server(datablock, conf["identity"])
    server.id = conf["label"]
    #if not args.ip:
    server.ip = conf["ip"]
    #else:
    #    server.ip = args.ip
    #if not args.port:
    server.port = conf["port"]
    #else:
    #    server.port = int(args.port)
    print("[*] Server created @ {}:{}".format(server.ip, server.port))
    return server


def create_worker(conf, datablock, cache):
    """
    Create a Client with supplied datablock and configured values to pull.
    :param conf: Dictionary holding configuration values. See: tools/loader.py
    :param datablock: Modbus datablock object.
    :return: ThreadClient object.
    """
    code = conf["code"]
    worker = Worker(datablock, code, cache)
    print("[*] Worker created.".format(worker.name))
    return worker

def create_cache(conf):
    cache = {}
    entities = {}
    for reg_label, values in conf.items():
        vals={}
        ent_vals={}
        dev, place = reg_label.split("-")
        vals["dev"] = dev
        vals["place"] = place
        vals["reg_type"] = values[0]
        vals["index"] = values[1]
        vals["datatype"] = values[2]
        vals["value"] = values[3]
        cache[reg_label]=vals
        if dev not in entities:
            if "sensor" in dev:
                ent_vals["etype"] = "sensor"
            elif "switch" in dev:
                ent_vals["etype"] = "switch"
                ent_vals["node"] = None
            else:
                continue
            entities[dev] = ent_vals
        if "node" in place:
            entities[dev]["node"] = place
        if "branch" in place:
            entities[dev]["branch"] = place
    return cache, entities


def broadcast_values(values, ip, port):
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.sendto(values.encode("utf-8"), (ip, port))

# content of the dvcd.loader
def load_rtu(path):
    print("[*] Loading configuration XML: '{}'.".format(path))
    conf = {}
    try:
        parser = xml.dom.minidom.parse(path)
        root = parser.documentElement

        label = root.getAttribute("label")
        ip = root.getElementsByTagName("ip")[0].childNodes[0].data
        port = int(root.getElementsByTagName("port")[0].childNodes[0].data)

        identity = {}
        identity_tag = root.getElementsByTagName("identity")[0]
        vendor_tag = identity_tag.getElementsByTagName("vendor")[0]
        identity["vendorname"] = vendor_tag.getAttribute("name")
        identity["vendorurl"] = vendor_tag.getAttribute("url")
        product_tag = identity_tag.getElementsByTagName("product")[0]
        identity["productname"] = product_tag.getAttribute("name")
        identity["productcode"] = product_tag.getAttribute("code")
        identity["modelname"] = product_tag.getAttribute("model")
        version_tag = identity_tag.getElementsByTagName("version")[0]
        identity["versionmajor"] = version_tag.getAttribute("major")
        identity["versionminor"] = version_tag.getAttribute("minor")

        registers = {}
        register_tags = root.getElementsByTagName("reg")
        for register_tag in register_tags:
            reg_datatype = register_tag.getAttribute("dt")
            reg_label = register_tag.getAttribute("label")
            reg_type = register_tag.getAttribute("type")
            reg_index = int(register_tag.getAttribute("index"))
            reg_value = register_tag.childNodes[0].data
            if reg_datatype == 'bool':
                if reg_value == "True" or reg_value == 1 or reg_value == 'T':
                    reg_value = bool(True)
                elif reg_value == "False" or reg_value == 0 or reg_value == 'F':
                    reg_value = bool(False)
            registers[reg_label] = [reg_type, reg_index, reg_datatype, reg_value]


        code = root.getElementsByTagName("code")[0].childNodes[0].data

        conf["label"] = label
        conf["ip"] = ip
        conf["port"] = port
        conf["identity"] = identity
        conf["registers"] = registers
        conf["code"] = code
    except:
        print("[-] Problem loading configuration XML: '{}'.".format(path))
        raise
    return conf

class UniqueKeyDict(dict):
    """A :class:`dict` that won't let you insert the same key twice."""
    def __setitem__(self, key, value):
        if key in self:
            raise KeyError('Key "%s" already exists in dict.' % key)
        super(UniqueKeyDict, self).__setitem__(key, value)

def make_eid(name, grid_idx):
    return '%s-%s' % (grid_idx, name)


#this class needs to be the connection to the pymodbus thingie. 