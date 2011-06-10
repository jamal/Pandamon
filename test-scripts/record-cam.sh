#!/bin/sh
gst-launch v4l2src ! video/x-raw-yuv,width=320,height=240 ! tee name=t ! queue ! ffmpegcolorspace ! theoraenc speed-level=2 quality=24 ! oggmux ! filesink location=test.ogv t. ! queue ! autovideosink
