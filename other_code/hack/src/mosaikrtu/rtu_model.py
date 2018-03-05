# rtu_model.py
"""
This module contains the RTU model with sensors and switches. 

"""
import xml.dom.minidom
from mosaikrtu.dvcd.data import DataBlock
from mosaikrtu.dvcd.server import Server
from mosaikrtu.dvcd.worker import Worker
from mosaikrtu.dvcd.com_server import com_server


import json
import math
import os.path
import sys

import threading
import time


def create_datablock(conf):
    """
    Create a Modbus datablock holding the registers described in the XML config file.
    :param conf: Dictionary holding configuration values. See: tools/loader.py
    :return: Modbus datablock object that locks when reading or writing.
    """
    datablock = DataBlock()
    regs = conf["registers"]
    for reg_label in regs:
        ty, addr, trusted, [value] = regs[reg_label]
        if value == "True":
            value = True
        elif value == "False":
            value = False
        elif "." in value:
            value = float(value)
        else:
            value = int(value)
        datablock.set(ty, addr, value)
        datablock.set('ir', addr, sys.maxsize)
    return datablock


def create_server(conf, datablock, rtueid):
    """
    Create a Server with supplied datablock and configured identity.
    :param conf: Dictionary holding configuration values. See: tools/loader.py
    :param datablock: Modbus datablock object.
    :return: Modbus Server object.
    """
    server = Server(datablock, conf["identity"], (conf["ip"], conf["port"]))
    server.id = conf["label"]
    print(
        rtueid + ": Server created @ {}:{}.".format(conf["ip"], conf["port"]))
    return server

def create_com_server():
    return com_server()


def create_worker(conf, datablock, cache, rtueid):
    """
    Create a Client with supplied datablock and configured values to pull.
    :param conf: Dictionary holding configuration values. See: tools/loader.py
    :param datablock: Modbus datablock object.
    :return: ThreadClient object.
    """
    worker = Worker(datablock, cache)
    print(rtueid + ": Worker created.".format(worker.name))
    return worker


def create_cache(conf):
    cache = {}
    entities = {}
    for reg_label, values in conf.items():
        vals = {}
        ent_vals = {}
        dev, place = reg_label.split("-")
        vals["dev"] = dev
        vals["place"] = place
        vals["reg_type"] = values[0]
        vals["index"] = values[1]
        vals["trusted"] = values[2]
        vals["value"] = values[3]
        cache[reg_label] = vals
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
            reg_label = register_tag.getAttribute("label")
            reg_trusted = register_tag.getAttribute("trusted")
            reg_type = register_tag.getAttribute("type")
            reg_index = int(register_tag.getAttribute("index"))
            reg_value = register_tag.childNodes[0].data
            registers[reg_label] = [reg_type, reg_index, reg_trusted, [reg_value]]
            # print(registers[reg_label])

        conf["label"] = label
        conf["ip"] = ip
        conf["port"] = port
        conf["identity"] = identity
        conf["registers"] = registers
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


# this class needs to be the connection to the pymodbus thingie.
