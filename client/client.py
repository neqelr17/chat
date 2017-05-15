import os
import sys
import zmq
import time
import json
import select
import argparse
import multiprocessing


class Client(multiprocessing.Process):
    def __init__(self, name, svr_addr, cli_addr):
        multiprocessing.Process.__init__(self)
        self.exit = multiprocessing.Event()
        self.name = name
        self.svr_addr = svr_addr
        self.cli_addr = cli_addr

    def run(self):
        context = zmq.Context()
        cli_sock = context.socket(zmq.DEALER)
        cli_sock.connect(self.cli_addr)

        svr_sock = context.socket(zmq.DEALER)
        svr_sock.connect('tcp://' + self.svr_addr)

        # Get connected
        connected = False
        print('Signing on...', end='')
        svr_sock.send_json({
            'cmd': 'logon',
            'name': self.name,
            })
        message = svr_sock.recv_json()
        if 'Welcome' in message['message']:
            print('Connected.')
            connected = True
        else:
            print('Failed.')
        print(message['message'])

        if connected:

            # We will poll the message queues.
            poller = zmq.Poller()
            poller.register(cli_sock, zmq.POLLIN)
            poller.register(svr_sock, zmq.POLLIN)

            while not self.exit.is_set():
                try:
                    sockets = dict(poller.poll(0.9))
                    if svr_sock in sockets:
                        msg = svr_sock.recv_json()
                        print("{} says: {}".format(
                            msg['who'], msg['message']))

                    if select.select([sys.stdin, ], [], [], 0.1)[0]:
                        req = sys.stdin.readline().rstrip()
                        if ':' in req:
                            name, msg = req.split(':')
                            svr_sock.send_json({
                                'cmd': 'say',
                                'who': name,
                                'msg': msg
                                })
                        else:
                            svr_sock.send_json({
                                'cmd': req
                                })
                except KeyboardInterrupt:
                    break

            # Disconnect nicely.
            print()
            print('Signing off...')
            svr_sock.send_json({
                'cmd': 'logoff',
                'name': self.name,
                })

        # Not connected, quit.
        # Tell the main process to quit.
        cli_sock.send_json({
            'cmd': 'quit'
            })
        cli_sock.close()
        svr_sock.close()

    def shutdown(self):
        """Clean shutdown of Process."""
        self.exit.set()


def main(name, server_addr):
    cli_addr = 'ipc://client.ipc'

    # Connect to transponder
    context = zmq.Context()
    cli_sock = context.socket(zmq.ROUTER)
    cli_sock.bind(cli_addr)

    # Reader reads from and sends data to the server
    client = Client(name, server_addr, cli_addr)
    client.run()

    poller = zmq.Poller()
    poller.register(cli_sock, zmq.POLLIN)

    while True:
        try:
            sockets = dict(poller.poll())

            if cli_sock in sockets:
                sender, message = cli_sock.recv_multipart()
                msg = json.loads(message.decode('utf8'))
                if 'cmd' in msg:
                    if msg['cmd'] == 'quit':
                        break

        except KeyboardInterrupt:
            client.shutdown()
            client.join()
            break

    cli_sock.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ZMQ Chat Client.')
    parser.add_argument('name', help='Your name.')
    parser.add_argument('server', help='Which server to talk to (HOST:PORT).  ie. 127.0.0.1:9000')
    args = parser.parse_args()

    main(args.name, args.server)
