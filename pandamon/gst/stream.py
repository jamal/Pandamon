import gobject
import gst

from codec import *


class Stream(gst.Pipeline):
    
    __gsttemplates__ = (
        gst.PadTemplate('sink', gst.PAD_SINK, gst.PAD_ALWAYS,
                        gst.caps_new_any())
    )

    def __init__(self, fd):
        gst.Bin.__init__(self)
        self.src = gst.element_factory_make('fdsrc')
        queue = gst.element_factory_make('queue')
        self.decoder = gst.element_factory_make('decodebin', 'decoder')
        self.decoder.connect('pad-added', self._on_decoder_pad_added) 
        self.add(self.src, queue, self.decoder)
        gst.element_link_many(self.src, queue, self.decoder)

        self.video_src = gst.element_factory_make('tee', 'video_src')
        self.audio_src = gst.element_factory_make('tee', 'audio_src')
        self.add(self.video_src, self.audio_src)

        self.src.set_property('fd', fd)

        bus = self.get_bus()
        bus.add_signal_watch()
        bus.connect('message', self._on_message)

        self.codecs = {}
        self.clients = {}
        self.on_eos = False

        self.resumeProducing()

    def __del__(self):
        self.set_state(gst.STATE_NULL)

    def _on_message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self.set_state(gst.STATE_NULL)
            if callable(self.on_eos):
                self.on_eos()
        elif message.type == gst.MESSAGE_ERROR:
            self.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            # FIXME: Should raise an exception
            print 'Error: %s' % err, debug

    def _on_decoder_pad_added(self, element, pad):
        video_caps = gst.Caps('video/x-raw-yuv', 'video/x-raw-rgb')
        audio_caps = gst.Caps('audio/x-raw-int', 'audio/x-raw-float')
        if pad.get_target().accept_caps(video_caps):
            pad.link(self.video_src.get_pad('sink'))
            fakesink = gst.element_factory_make('fakesink')
            self.add(fakesink)
            fakesink.sync_state_with_parent()
            self.video_src.link(fakesink)
        elif pad.get_target().accept_caps(audio_caps):
            pad.link(self.audio_src.get_pad('sink'))
            fakesink = gst.element_factory_make('fakesink')
            self.add(fakesink)
            fakesink.sync_state_with_parent()
            self.audio_src.link(fakesink)

    def add_client(self, format, fd):
        sink = self.add_codec(format)
        if sink:
            sink.emit('add', fd)
            sink.clients += 1

    def add_codec(self, format):
        format_codecs = {
            'mkv': MkvCodec,
            'ogg': OggCodec,
            'flv': FlvCodec,
        }

        if format not in format_codecs.keys():
            return False

        # FIXME: Check that the gst plugin has been registered first
        if format not in self.codecs.keys():
            codec = format_codecs[format]()
            self.add(codec)
            codec.sync_state_with_parent()

            video_sink = codec.get_request_pad('sink_%d')
            audio_sink = codec.get_request_pad('sink_%d')
            video_pad = self.video_src.get_request_pad('src%d')
            audio_pad = self.audio_src.get_request_pad('src%d')
            video_pad.link(video_sink)
            audio_pad.link(audio_sink)

            multifdsink = gst.element_factory_make('multifdsink')
            self.add(multifdsink)
            multifdsink.sync_state_with_parent()

            codec.get_static_pad('src').link(multifdsink.get_static_pad('sink'))
            multifdsink.connect('client-fd-removed', self._client_fd_removed)
            multifdsink.connect('client-removed', self._client_removed)
            multifdsink.clients = 0

            # FIXME: Will have to play with these values
            multifdsink.set_property('sync-method', 0)
            multifdsink.set_property('buffers-soft-max', 250)
            multifdsink.set_property('buffers-max', 500)

            self.codecs[format] = (codec, video_sink, 
                audio_sink, video_pad, audio_pad, multifdsink)
                                  
        else:
            (codec, video_sink, audio_sink, video_pad, audio_pad, 
                multifdsink) = self.codecs[format]

        return multifdsink

    def _remove_client(self, sink):
        sink.clients -= 1
        # FIXME: Free resources for codec

    def _client_fd_removed(self, sink, fd):
        self._remove_client(sink)

    def _client_removed(self, sink, fd, reason):
        self._remove_client(sink)

    def resumeProducing(self):
        print 'Resuming'
        self.set_state(gst.STATE_PLAYING)

    def pauseProducing(self):
        print 'Pausing'
        self.set_state(gst.STATE_PAUSED)

    def stopProducing(self):
        print 'Stopping'
        self.set_state(gst.STATE_NULL)

gobject.type_register(Stream)
