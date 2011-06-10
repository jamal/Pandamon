import pygtk
import gtk
import gobject
import pygst
import gst


class Main:

    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_title('Test Player')
        window.set_default_size(200, 200)
        window.connect('destroy', gtk.main_quit, 'WM destroy')
        vbox = gtk.VBox()
        window.add(vbox)
        self.button = gtk.Button('Add')
        self.button.connect('clicked', self.add_player)
        vbox.add(self.button)
        self.button = gtk.Button('Remove')
        self.button.connect('clicked', self.remove_player)
        vbox.add(self.button)
        window.show_all()
        
        self.player = gst.Pipeline('player')
        source = gst.element_factory_make('filesrc', 'test-source')
        source.set_property('location', '/home/jfanaian/Desktop/output.ogg')
        decoder = gst.element_factory_make('decodebin')
        decoder.connect('pad-added', self.on_pad_added)
        self.video_sink = gst.element_factory_make('tee', 'video-output')
        self.audio_sink = gst.element_factory_make('tee', 'audio-output')
        self.player.add(source, decoder, self.video_sink, self.audio_sink)
        gst.element_link_many(source, decoder)

        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self.on_message)

        self.player.set_state(gst.STATE_READY)
        
    def add_player(self, w):
        video_pad = self.player.get_by_name('video-output').get_request_pad('src%d')

        queue = gst.element_factory_make('queue')
        video_out = gst.element_factory_make('autovideosink')

        self.player.add(queue, video_out)
        gst.element_link_many(queue, video_out)
        video_pad.link(queue.get_static_pad('sink'))

        queue.set_state(gst.STATE_PLAYING)
        video_out.set_state(gst.STATE_PLAYING)

        if (self.player.get_state()[1] != gst.STATE_PLAYING):
            self.player.set_state(gst.STATE_PLAYING)

    def remove_player(self, w):
        pass
                        
    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            print 'Error: %s' % err, debug

    def on_pad_added(self, element, pad):
        try:
            sink = self.video_sink.get_static_pad('sink')
            pad.link(sink)
        except gst.LinkError:
            sink = self.audio_sink.get_static_pad('sink')
            pad.link(sink)

#class TestSrc(gst.Bin):
    #'''
    #'''

    #__gsttemplates__ = (
        #gst.PadTemplate(
            #'src%d',
            #gst.PAD_SRC,
            #gst.PAD_SOMETIMES,
            #gst.caps_new_any(),
        #)
    #)

    #def __init__(self, *args, **kwargs):
        #gst.BaseSrc.__init__(self, *args, **kwargs)

        #self.source = gst.element_factory_make('filesrc')
        #self.source.set_property('location', '/home/jfanaian/Desktop/output.ogg')
        #self.queue = gst.element_factory_make('queue')
        #self.decoder = gst.element_factory_make('decodebin')
        #self.decoder.connect('pad-added', self.on_pad_added)
        #self.add(self.source, self.queue, self.decoder)

    #def on_pad_added(self, element, pad):
        #pass

#gobject.type_register(TestSrc)
#gst.element_register(TestSrc, 'testsrc')

Main()
gtk.gdk.threads_init()
gtk.main()
