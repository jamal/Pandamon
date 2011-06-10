import sys

import pygst
pygst.require('0.10')

import gst

from twisted.internet import gtk2reactor
gtk2reactor.install()

from twisted.internet import defer, protocol, reactor
from twisted.internet.interfaces import IPushProducer

from zope.interface import implements


class TestProducerPipeline:

    def __init__(self):
        template = """
            alsasrc ! queue ! audioconvert ! vorbisenc ! 
                oggmux name=mux ! fdsink name=sink
            v4l2src ! queue ! videorate ! video/x-raw-yuv,width=640,height=480
                ! ffmpegcolorspace ! theoraenc bitrate=128 quality=28 ! mux.
            """
        #template = """
            #audiotestsrc ! queue ! audioconvert ! vorbisenc ! 
            #oggmux name=mux ! gdppay ! fdsink name=sink
            #videotestsrc ! queue ! theoraenc ! mux.
            #"""
        self.pipeline = gst.parse_launch(template)
        self.sink = self.pipeline.get_by_name('sink')


class ClientProtocol(protocol.Protocol):

    implements(IPushProducer)
    
    def connectionMade(self):
        print 'Connection made'
        self.producer = TestProducerPipeline()
        self.transport.write('stream %s' % self.factory.stream)
        reactor.callLater(0, self._sendStream)

    def _sendStream(self):
        self.transport.registerProducer(self, True)
        self.producer.sink.set_property('fd', self.transport.fileno())
        self.resumeProducing()

    def resumeProducing(self):
        print 'Resume producing'
        self.producer.pipeline.set_state(gst.STATE_PLAYING)

    def pauseProducing(self):
        print 'Pause producing'
        self.producer.pipeline.set_state(gst.STATE_PAUSED)

    def stopProducing(self):
        print 'Stop producing'
        self.producer.pipeline.set_state(gst.STATE_NULL)
        self.transport.loseConnection()


class ClientFactory(protocol.ReconnectingClientFactory):

    protocol = ClientProtocol

    def __init__(self, stream):
        self.stream = stream


if len(sys.argv) > 1:
    stream = sys.argv[1]
else:
    stream = 'test'

#reactor.connectTCP('publish.pandamon.jamalfanaian.com', 8800, ClientFactory(stream))
reactor.connectTCP('localhost', 8800, ClientFactory(stream))
reactor.run()
