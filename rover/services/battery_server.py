#!/usr/bin/env python3
"""Server for multithreaded (asynchronous) chat application."""
from socket import AF_INET, socket, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
from datetime import datetime
import logging, atexit, time

log_file = '/home/rover_logs/comm_server-log-' + datetime.now().strftime("%m-%d-%y") + '.txt'
logging.basicConfig(filename=log_file,level=logging.DEBUG)
logging.info('===== Rover Battery Capacity Communications Server Logging Started ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))

def shutdown():
    logging.info('Exceptions occurred to battery, shutting down sockets.')
    try:
        SERVER.send(bytes('{quit}', 'utf8'))
    except: pass
    try:
        SERVER.close
    except: pass
atexit.register(shutdown)

def accept_incoming_connections():
    """Sets up handling for incoming clients."""
    while True:
        client, client_address = SERVER.accept()
        logging.debug("%s:%s Battery has connected." % client_address)
        client.send(bytes("Connected", 'utf8'))
        addresses[client] = client_address
        Thread(target=handle_client, args=(client,)).start()

def handle_client(client):  # Takes client socket as argument.
    """Handles a single client connection."""
    name = client.recv(128).decode('utf8')
    client.send(bytes('Active', 'utf8'))
    logging.debug(name + ' joined Battery @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
    clients[client] = name

    while True:
        time.sleep(.1)
        msg = ''
        msg = client.recv(128)
        if str(msg) != '':    # Dump bogus msg received
            logging.debug('Battery message received: ' + str(msg) + ' from: ' + str(name) + ' @ ' + datetime.now().strftime("%m-%d-%y %H:%M:%S"))
            if msg != bytes('{quit}', 'utf8'):    # Handle msg received that's not {quit}
#                logging.debug('broadcast msg = ' + str(name) + ': ' + str(msg))
                broadcast(msg, name+": ")
            else:
                client.send(bytes('{quit}', 'utf8'))
                client.close()
                del clients[client]
                logging.debug("%s has left the Battery session." % name)
                break

def broadcast(msg, prefix=""):  # prefix is for name identification.
    """Broadcasts a message to all the clients."""
    for sock in clients:
        sock.send(bytes(prefix, 'utf8')+msg)
        
clients = {}
addresses = {}

HOST = ''
PORT = 33002
ADDR = (HOST, PORT)

SERVER = socket(AF_INET, SOCK_STREAM)
SERVER.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
SERVER.bind(ADDR)

if __name__ == "__main__":
    SERVER.listen(5)
    logging.debug("Waiting for Battery connections...")
    ACCEPT_THREAD = Thread(target=accept_incoming_connections)
    ACCEPT_THREAD.start()
    ACCEPT_THREAD.join()
    SERVER.close()
