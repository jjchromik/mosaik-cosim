import socket

udp_ip = "192.168.33.255"
udp_port = 10505
message = "blah"

print("UDP target IP: {}".format(udp_ip))
print("UDP target port: {}".format(udp_port))
print("message: {}".format(message))

sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM)  # UDP

sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.sendto(message.encode("utf-8"), (udp_ip, udp_port))