import socket

udp_ip = ""
udp_port = 10505

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((udp_ip, udp_port))


while True:
    data, addr = sock.recvfrom(2048) # buffer size is 1024 bytes
    print("received message: {}".format(data.decode('utf-8')))