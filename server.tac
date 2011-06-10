from twisted.internet import glib2reactor
glib2reactor.install()

from twisted.application import internet, service
from twisted.web import server

from pandamon.server import Service

application = service.Application('test-server')
f = Service()
serviceCollection = service.IServiceCollection(application)
internet.TCPServer(8800, f.getHttpFactory()).setServiceParent(serviceCollection)
# RTMP Support is currently being tested
#internet.TCPServer(1935, f.getRtmpFactory()).setServiceParent(serviceCollection)
internet.TCPServer(8801, server.Site(f.getHttpResource())).setServiceParent(serviceCollection)
