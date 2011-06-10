import logging
import os
import select

from twisted.application import internet, service
from twisted.internet import protocol, reactor, defer
from twisted.python import log
from twisted.web import resource, server
from twisted.web.error import NoResource

#import sys
#sys.path = ['/home/jfanaian/devel/.priv/rtmp'] + sys.path
#from rtmpy import server as rtmp_server
#from rtmpy.rtmp import event

from pandamon.gst import stream


class HttpResource(resource.Resource):

    def __init__(self, service, stream=None, format=None):
        print 'Init with stream', stream
        self.service = service
        self.stream = stream
        self.format = format
        resource.Resource.__init__(self)

    def _writeHeaders(self, request):
        fd = request.transport.fileno()
        request.setHeader('Server', 'PandamonServer')
        request.setHeader('Connection', 'close')
        request.setHeader('Cache-Control', 'no-cache')
        request.setHeader('Cache-Control', 'private')
        request.setHeader('Content-Type', 'application/ogg')

        headers = []
        for name, value in request.headers.items():
            headers.append('%s: %s' % (name.capitalize(), value))

        print 'Writing headers'
        os.write(fd, 'HTTP/1.0 200 OK\r\n%s\r\n\r\n' % '\r\n'.join(headers))

    def render_GET(self, request):
        if self.stream and self.format:
            fd = request.transport.fileno()
            request.transport.stopReading()

            self._writeHeaders(request)
            self.service.addStreamClient(self.stream, self.format, fd)

        return server.NOT_DONE_YET

    def getChild(self, child, request):
        print 'Get Child', child
        path, format = child.split('.')

        if self.service.streamExists(path):
            return HttpResource(self.service, path, format)

        return NoResource()


class HttpProtocol(protocol.Protocol):

    def connectionMade(self):
        print 'Client connected'
        self.stream_name = ''

    def dataReceived(self, data):
        cmd, params = data.split(' ')
        if cmd == 'stream':
            self.stream_name = params

            # Take over the twisted socket
            self.transport.stopReading()
            self.transport.stopWriting()

            stream = self.factory.createStream(self.stream_name, self.transport.fileno())
            stream.on_eos = self.eos

    def eos(self):
        self.connectionLost('Client closed connection')

    def connectionLost(self, reason):
        print 'Client connection lost'
        self.factory.deleteStream(self.stream_name)


#class RtmpApplication(rtmp_server.Application):
#    
#    app = "video"
#
#    def onConnect(self, client, **kwargs):
#        self.acceptConnection(client)
#
#    def onPlay(self, client, stream):
#        # FIXME: Need to support multpile clients
#        self.protocol = client.protocol
#
#        # NetStream.Play.Reset and NetStream.Play.Start need to be sent here
#        s = self.protocol.getStream(1)
#
#        # GET READY TO FACEPLODE
#        transport = client.protocol.transport
#        transport.stopReading()
#
#        print "Rtmp Play Stream", stream
#        self.service_factory.addStreamClient(stream, 'flv', transport.fileno())


class Service(service.Service):

    def __init__(self):
        self.streams = {}

    def createStream(self, name, fd):
        if name in self.streams:
            NameError("Stream %s already exists" % name)
        s = stream.Stream(fd)
        self.streams[name] = s
        print "Created stream %s" % name
        return s

    def streamExists(self, name):
        if name in self.streams:
            return True
        return False

    def deleteStream(self, name):
        if name not in self.streams:
            return NameError("Stream %s doesn't exist" % name)
        del self.streams[name]

    def addStreamClient(self, name, format, fd):
        if name not in self.streams:
            # Should raise an exception
            return False

        s = self.streams[name]
        return s.add_client(format, fd)
        
    def getHttpFactory(self):
        f = protocol.ServerFactory()
        f.protocol = HttpProtocol
        f.createStream = self.createStream
        f.deleteStream = self.deleteStream
        return f

    def getHttpResource(self):
        r = HttpResource(self)
        return r

#    def getRtmpFactory(self):
#        f = rtmp_server.ServerFactory()
#        r = RtmpApplication()
#        r.service_factory = self
#        f.registerApplication("video", r)
#        return f
