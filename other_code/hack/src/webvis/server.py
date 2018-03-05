"""
This module contains a simple simpy.io based webserver with websockets.

"""
import json
import logging
import mimetypes
import os.path
import time

from simpy.io import select as backend
from simpy.io.http import Service
from simpy.io.websocket import WebSocket


logger = logging.getLogger(__name__)

UPDATE_INTERVAL = 0.1
RTU_FIX_SHOW_TIME = 5.0


class Server(object):

    """
    TCP server for the web visualisation.
    """

    def __init__(self, env, server_sock):
        self.env = env
        self.server_sock = server_sock
        self.websocket = None

        self.basedir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                    'html'))
        """Base directory for static files."""

        self.topology_ready = env.event()
        self.topology = None
        self.data_buf = None
        self.wait_for_update = []  # List of events to be triggered on updates
        self.wait_for_attack = []
        self._reset_data_buf()
        self.highlighting = None

        self.env.process(self._broadcast_update())
        self.env.process(self._serve())

    def _broadcast_update(self):
        """
        Broadcasts the data to the visualisation.
        """
        while True:
            yield self.env.timeout(UPDATE_INTERVAL)
            new_data = self._reset_data_buf()
            if new_data['progress'] is not None:
                msg = json.dumps(['update_data', new_data])
                for evt in self.wait_for_update:
                    evt.succeed(msg)
                self.wait_for_update = []

    def _serve(self):
        """
        Webserver main process.
        """
        while True:
            sock = yield self.server_sock.accept()
            service = Service(sock)
            self.env.process(self.handler(service))

    def handler(self, service):
        """
        Handle client requests.
        Either serve static files or create a websocket.
        :param service: service to handel
        """
        try:
            while True:
                request = yield service.recv()
                yield request.read(all=True)

                uri = request.uri
                if uri.endswith('/'):
                    uri += 'index.html'

                if uri == '/websocket':
                    self.env.process(self.websock(service, request))
                    break

                if uri == '/hacker_tools':
                    self.env.process(self.hacker_tools(service, request))
                    break

                if uri == '/rtu_worker':
                    self.env.process(self.rtu_worker(service, request))
                    break

                try:
                    ctype, data = self.serve_static(uri)
                except ValueError:
                    yield request.respond(404, {
                        'content-type': 'text/plain; charset=utf-8',
                    }, data=b'Not found')
                else:
                    yield request.respond(200, {
                        'content-type': ctype,
                    }, data=data)

        except ConnectionError:
            logger.warn('socket ConnectionError in "Server.handler()"')

    def websock(self, service, request):
        """
        Process for websocket connections.
        :param service: service to handle
        :param request: the services request
        """
        excess_data = service.decommission()
        self.websocket = WebSocket(service.sock)
        self.websocket.configure(False, headers=request.headers)

        try:
            msg = yield self.websocket.read()
            assert msg == 'get_topology'
            yield self.topology_ready
            self.links = self.topology['links']
            yield self.websocket.write(json.dumps(['setup_topology', self.topology]))

            while True:
                evt_new_data = self.env.event()
                self.wait_for_update.append(evt_new_data)
                msg = yield evt_new_data
                yield self.websocket.write(msg)

        except ConnectionError:
            logger.warn('websocket ConnectionError in "Server.websock()"')
        except OSError as e:
            logger.warn('websocket OSError in "Server.websocket()": %s' % e)

    def hacker_tools(self, service, request):
        """
        Process for hacker tools connections.
        :param service: service to handle
        :param request: the services request
        """
        try:
            while True:
                msg = yield service.sock.read(amount=1024)
                msgs = msg.decode()
                attacks = json.loads(msgs)
                self.set_new_attacks(attacks)

        except ConnectionError:
            logger.warn(
                'hacker_tools ConnectionError in "Server.hacker_tools()"')
        except OSError as e:
            logger.warn(
                'hacker_tools OSError in "Server.hacker_tools()": %s' % e)

    def rtu_worker(self, service, request):
        """
        Process for rtu worker connections.
        :param service: service to handle
        :param request: the services request
        """
        try:
            while True:
                msg = yield service.sock.read(amount=1024)
                msgs = msg.decode()
                fixes = json.loads(msgs)
                self.set_new_fixes(fixes)

        except ConnectionError:
            logger.warn('rtu_worker ConnectionError in "Server.rtu_worker()"')
        except OSError as e:
            logger.warn('rtu_worker OSError in "Server.rtu_worker()": %s' % e)

    def serve_static(self, uri):
        """
        Try to read and return a static file and its mime type.
        :param uri: file to serve
        """
        req_path = os.path.abspath(os.path.join(self.basedir, uri.lstrip('/')))
        if not req_path.startswith(self.basedir):
            raise ValueError
        if not os.path.isfile(req_path):
            raise ValueError

        content_type = mimetypes.guess_type(req_path)[0]
        if content_type.startswith('text/'):
            content_type = '%s; charset=utf-8' % content_type
        return content_type, open(req_path, 'rb').read()

    def set_new_data(self, sim_time, progress, node_data):
        """
        Sets new data to transfer to the JS script.
        :param sim_time: simulation time
        :param progress: pro centual progress in the simualtion
        :param node_data: data of the nodes
        """
        if self.highlighting == None:
            self._reset_highlighting()
        self.data_buf['time'] = sim_time
        self.data_buf['progress'] = progress
        self.data_buf['node_data'].append(node_data)
        self.data_buf['a_branches'].append(
            self.highlighting['a_branches'])
        self.data_buf['a_nodes'].append(self.highlighting['a_nodes'])
        cur_time = int(round(time.time() * 1000))
        for b in self.highlighting['f_branches']:
            if cur_time > b[1]:
                self.highlighting['f_branches'].remove(b)
            else:
                self.data_buf['f_branches'].append(b[0])
        for n in self.highlighting['f_nodes']:
            if cur_time > n[1]:
                self.highlighting['f_nodes'].remove(n)
            else:
                self.data_buf['f_nodes'].append(n[0])

    def _reset_data_buf(self):
        """
        Resets the data buffer.
        """
        data = self.data_buf
        self.data_buf = {
            'time': None,
            'progress': None,
            'node_data': [],
            'a_branches': [],
            'a_nodes': [],
            'f_branches': [],
            'f_nodes': [],
        }
        return data

    def set_new_attacks(self, attacks):
        """
        Sets new attack highlighting for transfer to the visualisation.
        :param attacks: attacks to highlight
        """
        for atk in attacks:
            if "node" in atk:
                if atk not in self.highlighting['a_nodes']:
                    self.highlighting['a_nodes'].append(atk)
            else:
                if atk not in self.highlighting['a_branches']:
                    self.highlighting['a_branches'].append(atk)

    def set_new_fixes(self, fixes):
        """
        Sets new fix highlighting for transfer to the visualisation.
        :param fixes: fixes to highlight
        """
        cur_time = int(round(time.time() * 1000))
        end_time = cur_time + RTU_FIX_SHOW_TIME * 1000
        for fix in fixes:
            if "node" in fix:
                self.highlighting['f_nodes'].append([fix, end_time])
                if fix in self.highlighting['a_nodes']:
                    self.highlighting['a_nodes'].remove(fix)
            else:
                if fix[-1] == 'a':
                    fix = fix[:-1]
                for b in self.highlighting['f_branches']:
                    if fix in b[0]:
                        self.highlighting['f_branches'].remove(b)
                self.highlighting['f_branches'].append([fix, end_time])
                if fix in self.highlighting['a_branches']:
                    self.highlighting['a_branches'].remove(fix)

    def _reset_highlighting(self):
        """
        Resets the highlighting data.
        :return: current data before the reset
        """
        data = self.highlighting
        self.highlighting = {
            'a_branches': [],
            'a_nodes': [],
            'f_branches': [],
            'f_nodes': [],
        }
        return data


if __name__ == '__main__':
    addr = ('localhost', 8000)

    env = backend.Environment()
    server_sock = backend.TCPSocket.server(env, addr)
    server = Server(env, server_sock)

    env.run()
