#! /usr/bin/env python

import pygst
import ElementBase
pygst.require("0.10")
import gst
import gobject

import base64

import Queue, traceback
import pyccn

from ElementBase import CCNDepacketizer

CMD_SEEK = 1

def debug(cls, text):
	print "%s: %s" % (cls.__class__.__name__, text)

class CCNAudioDepacketizer(CCNDepacketizer):
	pass

class AudioSrc(ElementBase.CCNElementSrc):
	__gtype_name__ = 'AudioSrc'
	__gstdetails__ = ("CCN Audio Source", "Source/Network",
		"Receives audio data over a CCNx network", "Derek Kulinski <takeda@takeda.tk>")

	__gsttemplates__ = (
		gst.PadTemplate("src",
			gst.PAD_SRC,
			gst.PAD_ALWAYS,
			gst.caps_new_any()),
		)

	__gproperties__ = {
		'location' : (gobject.TYPE_STRING,
			'CCNx location',
			'location of the stream in CCNx network',
			'',
			gobject.PARAM_READWRITE),
		'publisher' : (gobject.TYPE_STRING,
			'Publisher ID',
			'base64 encoding of publisher\'s public key',
			'',
			gobject.PARAM_READWRITE)
	}

	def do_set_property(self, property, value):
		if property.name == 'location':
			self.depacketizer = CCNAudioDepacketizer(value, 3)
		elif property.name == 'publisher':
			self.depacketizer.publisher_id = base64.b64decode(value)
		else:
			raise AttributeError, 'unknown property %s' % property.name

gst.element_register(AudioSrc, 'AudioSrc')

if __name__ == '__main__':
	import sys

	gobject.threads_init()

	if len(sys.argv) != 2:
		print "Usage: %s <uri>" % sys.argv[0]
		sys.exit(1)

	uri = sys.argv[1]

	pipeline = gst.parse_launch('AudioSrc location=%s ! decodebin ! autoaudiosink' % uri)

	loop = gobject.MainLoop()

	pipeline.set_state(gst.STATE_PLAYING)
	print "Entering loop"

	try:
		loop.run()
	except KeyboardInterrupt:
		print "Ctrl+C pressed, exitting"
		pass

	pipeline.set_state(gst.STATE_NULL)
	pipeline.get_state(gst.CLOCK_TIME_NONE)
