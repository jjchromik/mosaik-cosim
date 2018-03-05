import xml.dom.minidom


COMPATIBLE_VERSION = ["0.5"]


def loader(path):
    """
    Open XML configuration file. Get all information.
    :param path: String with the path to config file.
    :return: Dict[config_label]: config_value
    """
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
            reg_type = register_tag.getAttribute("type")
            reg_index = int(register_tag.getAttribute("index"))
            reg_value = register_tag.childNodes[0].data
            registers[reg_label] = [reg_type, reg_index, [reg_value]]

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
