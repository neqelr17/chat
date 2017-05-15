import zmq
import json
import argparse


def say(source, message):
    """Make a dict of source and message."""
    return {
        'who': source,
        'message': message
    }


class ChatServer():
    """Chat Server."""

    def logon(self, client, request):
        """Process logon request."""
        found = False
        for cli in self.clients:
            if cli['name'] == request['name']:
                found = True
        if not found:
            self.clients.append({
                'addr': client,
                'name': request['name'],
            })
            return say('Server', 'Welcome, ' + request['name'] + '!')
        else:
            return say('Server', 'Username already taken.')

    def logoff(self, client, request):
        """Process logoff request."""
        found = None
        for cli in self.clients:
            if cli['name'] == request['name'] and \
               cli['addr'] == client:
                found = cli
        if found:
            self.clients.remove(found)
            return say('Server', 'cya!')
        return None

    def list(self, client, request):
        """Process list request."""
        client_list = []
        for cli in self.clients:
            client_list.append(cli['name'])
        return say('Server', client_list)

    def say(self, client, request):
        """Process say request."""
        name = None
        for cli in self.clients:
            if cli['addr'] == client:
                name = cli['name']
        if name:
            who = request['who']
            msg = request['msg']
            for cli in self.clients:
                if cli['name'] == who or who == 'all':
                    self.sock.send_multipart([
                        cli['addr'],
                        json.dumps(say(name, msg)).encode('utf8')
                        ])
            return None
        else:
            return say('Server', 'who are you?')

    def __init__(self, port):
        """Initialization: reqiures port number."""
        self.clients = []
        self.port = port
        self.sock = None

        self.process = {
            'logon': self.logon,
            'logoff': self.logoff,
            'list': self.list,
            'say': self.say
        }

    def run(self):
        """Main server loop."""
        context = zmq.Context()
        self.sock = context.socket(zmq.ROUTER)
        self.sock.bind('tcp://*:' + self.port)

        poller = zmq.Poller()
        poller.register(self.sock, zmq.POLLIN)

        while True:
            sockets = dict(poller.poll())

            if self.sock in sockets:
                client, message = self.sock.recv_multipart()
                request = json.loads(message.decode('utf8'))
                print('processing request:', request)
                try:
                    reply = self.process[request['cmd']](client, request)
                    if reply:
                        self.sock.send_multipart([
                            client,
                            json.dumps(reply).encode('utf8')
                            ])
                except KeyError:
                    self.sock.send_multipart([
                        client,
                        json.dumps(say('Server', 'what?')).encode('utf8')
                        ])


def main(port):
    server = ChatServer(port)
    server.run()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='ZMQ Chat Server.')
    parser.add_argument('port', help='Which port the server will run on.')
    args = parser.parse_args()

    main(args.port)
