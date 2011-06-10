#!/bin/sh
gst-launch v4l2src ! video/x-raw-yuv,width=640,height=480 ! autovideosink

