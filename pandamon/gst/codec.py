import gobject
import gst


class Codec(gst.Bin):

    video_caps = gst.Caps('video/x-raw-yuv', 'video/x-raw-rgb')
    
    audio_caps = gst.Caps('audio/x-raw-int', 'audio/x-raw-float')
    
    def __init__(self):
        gst.Bin.__init__(self)
        
        self.add(self.muxer)
        self.muxer.sync_state_with_parent()
        srcpad = gst.GhostPad('src', self.muxer.get_static_pad('src'))
        srcpad.set_active(True)
        self.add_pad(srcpad)
        self.pad_count = 0
        self.pads = {}
        self.inputs = {}

    def do_request_new_pad(self, template, name=None):
        if name == None:
            name = 'sink_%u' % self.pad_count

        pad = gst.ghost_pad_new_notarget(name, gst.PAD_SINK)
        pad.set_active(True)
        self.add_pad(pad)
        pad.connect('linked', self._on_pad_linked)
        self.pads[name] = pad
        self.pad_count += 1
        return pad

    def _on_pad_linked(self, pad, peer, user_data=None):
        if peer.accept_caps(self.video_caps):
            self.video_pad_linked(pad, peer, user_data)
        elif peer.accept_caps(self.audio_caps):
            self.audio_pad_linked(pad, peer, user_data)

    def do_release_pad(self, pad):
        name = pad.get_name()
        if name in self.input.keys():
            pad, queue, encoder, muxerpad = self.inputs.pop(name)
            encoder.get_pad('src').set_active(False)
            self.muxer.release_request_pad(muxerpad)
            encoder.get_pad('src').unlink(muxerpad)
            queue.unlink(encoder)
            queue.set_state(gst.STATE_NULL)
            encoder.set_state(gst.STATE_NULL)
            self.remove(queue, encoder)
            self.remove_pad(pad)


class MkvCodec(Codec):

    caps = gst.Caps(
        'audio/x-raw-float',
        'video/x-raw-yuv',
    )

    __gsttemplates__ = (
        gst.PadTemplate('sink_%d', gst.PAD_SINK, gst.PAD_REQUEST, caps),
        gst.PadTemplate('src', gst.PAD_SRC, gst.PAD_ALWAYS,
                        gst.Caps('application/ogg'))
    )

    def __init__(self):
        self.muxer = gst.element_factory_make('matroskamux', 'muxer')
        Codec.__init__(self)
        
    def video_pad_linked(self, pad, peer, user_data=None):
        queue = gst.element_factory_make('queue')
        videorate = gst.element_factory_make('videorate')
        colorspace = gst.element_factory_make('ffmpegcolorspace')
        videoscale = gst.element_factory_make('videoscale')
        caps = gst.Caps('video/x-raw-yuv, width=320, height=240')
        filter = gst.element_factory_make('capsfilter')
        filter.set_property('caps', caps)
        encoder = gst.element_factory_make('vp8enc')
        self.add(queue, videorate, colorspace, videoscale, filter, encoder)
        for e in [queue, videorate, colorspace, videoscale, filter, encoder]:
            e.sync_state_with_parent()
        gst.element_link_many(queue, videorate, colorspace, videoscale, filter, encoder)
        pad.set_target(queue.get_pad('sink'))
        muxerpad = self.muxer.get_request_pad('video_%d')
        encoder.get_pad('src').link(muxerpad)
        
        self.inputs[pad.get_name()] = (pad, queue, encoder, muxerpad)
        
    def audio_pad_linked(self, pad, peer, user_data=None):
        queue = gst.element_factory_make('queue')
        audioconv = gst.element_factory_make('audioconvert')
        encoder = gst.element_factory_make('vorbisenc')
        self.add(queue, audioconv, encoder)
        for e in [queue, audioconv, encoder]:
            e.sync_state_with_parent()
        gst.element_link_many(queue, audioconv, encoder)
        pad.set_target(queue.get_pad('sink'))
        muxerpad = self.muxer.get_request_pad('audio_%d')
        encoder.get_pad('src').link(muxerpad)
        
        self.inputs[pad.get_name()] = (pad, queue, encoder, muxerpad)

gobject.type_register(MkvCodec)


class OggCodec(Codec):

    caps = gst.Caps(
        'audio/x-raw-float',
        'video/x-raw-yuv',
    )

    __gsttemplates__ = (
        gst.PadTemplate('sink_%d', gst.PAD_SINK, gst.PAD_REQUEST, caps),
        gst.PadTemplate('src', gst.PAD_SRC, gst.PAD_ALWAYS,
                        gst.Caps('application/ogg'))
    )

    def __init__(self):
        self.muxer = gst.element_factory_make('oggmux', 'muxer')
        Codec.__init__(self)
        
    def video_pad_linked(self, pad, peer, user_data=None):
        queue = gst.element_factory_make('queue')
        videorate = gst.element_factory_make('videorate')
        colorspace = gst.element_factory_make('ffmpegcolorspace')
        videoscale = gst.element_factory_make('videoscale')
        caps = gst.Caps('video/x-raw-yuv, width=320, height=240')
        filter = gst.element_factory_make('capsfilter')
        filter.set_property('caps', caps)
        encoder = gst.element_factory_make('theoraenc')
        encoder.set_property('bitrate', 128)
        self.add(queue, videorate, colorspace, videoscale, filter, encoder)
        for e in [queue, videorate, colorspace, videoscale, filter, encoder]:
            e.sync_state_with_parent()
        gst.element_link_many(queue, videorate, colorspace, videoscale, filter, encoder)
        pad.set_target(queue.get_pad('sink'))
        muxerpad = self.muxer.get_request_pad('sink_%d')
        encoder.get_pad('src').link(muxerpad)
        
        self.inputs[pad.get_name()] = (pad, queue, encoder, muxerpad)
        
    def audio_pad_linked(self, pad, peer, user_data=None):
        queue = gst.element_factory_make('queue')
        audioconv = gst.element_factory_make('audioconvert')
        encoder = gst.element_factory_make('vorbisenc')
        self.add(queue, audioconv, encoder)
        for e in [queue, audioconv, encoder]:
            e.sync_state_with_parent()
        gst.element_link_many(queue, audioconv, encoder)
        pad.set_target(queue.get_pad('sink'))
        muxerpad = self.muxer.get_request_pad('sink_%d')
        encoder.get_pad('src').link(muxerpad)
        
        self.inputs[pad.get_name()] = (pad, queue, encoder, muxerpad)

gobject.type_register(OggCodec)


class FlvCodec(Codec):

    sink_caps = gst.Caps(
        'audio/x-raw-int',
        'video/x-raw-yuv',
        'video/x-raw-rgb',
        'video/x-raw-gray',
    )

    src_caps = gst.Caps(
        'video/x-flv',
    )

    __gsttemplates__ = (
        gst.PadTemplate('sink_%d', gst.PAD_SINK, gst.PAD_REQUEST, sink_caps),
        gst.PadTemplate('src', gst.PAD_SRC, gst.PAD_ALWAYS, src_caps),
    )

    def __init__(self):
        self.muxer = gst.element_factory_make('flvmux', 'muxer')
        Codec.__init__(self)
        
    def video_pad_linked(self, pad, peer, user_data=None):
        queue = gst.element_factory_make('queue')
        videorate = gst.element_factory_make('videorate')
        colorspace = gst.element_factory_make('ffmpegcolorspace')
        videoscale = gst.element_factory_make('videoscale')
        caps = gst.Caps('video/x-raw-yuv, width=320, height=240')
        filter = gst.element_factory_make('capsfilter')
        filter.set_property('caps', caps)
        encoder = gst.element_factory_make('ffenc_flv')
        self.add(queue, videorate, colorspace, videoscale, filter, encoder)
        for e in [queue, videorate, colorspace, videoscale, filter, encoder]:
            e.sync_state_with_parent()
        gst.element_link_many(queue, videorate, colorspace, videoscale, filter, encoder)
        pad.set_target(queue.get_pad('sink'))
        muxerpad = self.muxer.get_request_pad('video')
        encoder.get_pad('src').link(muxerpad)
        
        self.inputs[pad.get_name()] = (pad, queue, encoder, muxerpad)
        
    def audio_pad_linked(self, pad, peer, user_data=None):
        queue = gst.element_factory_make('queue')
        audioconv = gst.element_factory_make('audioconvert')
        encoder = gst.element_factory_make('lame')
        parser = gst.element_factory_make('mp3parse')
        self.add(queue, audioconv, encoder, parser)
        for e in [queue, audioconv, encoder, parser]:
            e.sync_state_with_parent()
        gst.element_link_many(queue, audioconv, encoder, parser)
        pad.set_target(queue.get_pad('sink'))
        muxerpad = self.muxer.get_request_pad('audio')
        parser.get_pad('src').link(muxerpad)
        
        self.inputs[pad.get_name()] = (pad, queue, encoder, muxerpad)

gobject.type_register(FlvCodec)


if __name__ == '__main__':
    import sys, os
    import pygtk, gtk, gobject
    import pygst

    class Test:

        def __init__(self):
            self.pipeline = gst.Pipeline()
            video = gst.element_factory_make('videotestsrc')
            audio = gst.element_factory_make('audiotestsrc')
            codec = FlvCodec()
            decodebin = gst.element_factory_make('decodebin')
            decodebin.connect('pad-added', self.decoder_pad_added)
            self.pipeline.add(video, audio, codec, decodebin)

            video.get_static_pad('src').link(codec.get_request_pad('sink_%d'))
            audio.get_static_pad('src').link(codec.get_request_pad('sink_%d'))
            codec.get_static_pad('src').link(decodebin.get_static_pad('sink'))

            self.pipeline.set_state(gst.STATE_PLAYING)

        def decoder_pad_added(self, element, pad):
            video_caps = gst.Caps('video/x-raw-yuv', 'video/x-raw-rgb')
            audio_caps = gst.Caps('audio/x-raw-int', 'audio/x-raw-float')
            if pad.get_target().accept_caps(video_caps):
                sink = gst.element_factory_make('autovideosink')
                self.pipeline.add(sink)
                pad.link(sink.get_static_pad('sink'))
                sink.sync_state_with_parent()
            elif pad.get_target().accept_caps(audio_caps):
                sink = gst.element_factory_make('autoaudiosink')
                self.pipeline.add(sink)
                pad.link(sink.get_static_pad('sink'))
                sink.sync_state_with_parent()

    Test()
    gtk.gdk.threads_init()
    gtk.main()

