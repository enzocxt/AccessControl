#! /usr/bin/env python
import pygst
pygst.require("0.10")
import gst
import gobject

import sys, threading, os, time
import pyccn

import utils
from video_sink import VideoSink

def debug(cls, text):
	print "%s: %s" % (cls.__class__.__name__, text)

class VideoSite:
	def __init__(self, uri):
		self.pipeline = gst.parse_launch("""
			filesrc location=/home/enzo/Videos/Part_Of_Me_15.mp4 !
			typefind ! qtdemux name=mux mux.video_00 ! queue ! 
			VideoSink location=%s
		""" % uri)
		
		freshness = 30 * 30
		self.loop = gobject.MainLoop()

		self.publisher = utils.RepoSocketPublisher()	

		self._handle = pyccn.CCN()
		self._get_handle = pyccn.CCN()

		self._basename = pyccn.Name('/test/VideoSite')
		self._user_basename = self._basename.append('User')
		self._register_info_name = self._user_basename.append('Register_Info')
		# '/test/VideoSite/User/Register_Info'

		self._key = pyccn.CCN.getDefaultKey()
		# _name_key is the name of the content object for client to get the public key
		self._name_key = self._basename.append('Key')
		self._signed_info = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._name_key), freshness = freshness)
		self._singed_info_frames = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._name_key), freshness = 1)

		# client list
		self.client = []

		# key for encrypting content
		self._dataKey_flag = False # if True, data key has been published
#		self._data_key = os.urandom(16)
		self._data_key = '123456789asdfghj'
		self._name_of_dataKey = self._basename.append('Movie')
		self._name_of_dataKey = self._name_of_dataKey.append('DataKey')
		# '/test/VideoSite/Movie/DataKey'

		# publish the public key
#		signed_info = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._key), freshness = freshness)
#		co = pyccn.ContentObject(self._name_key, self._key.publicToDER(), signed_info)
#		co.sign(self._key)
#		self.publisher.put(co)

	# publish the video content
	def run(self):
		gobject.threads_init()
		self.pipeline.set_state(gst.STATE_PLAYING)

		try:
			self.loop.run()
		except KeyboardInterrupt:
			print "Ctrl+c pressed, exiting"
			pass

		self.pipeline.set_state(gst.STATE_NULL)
		self.pipeline.get_state(gst.CLOCK_TIME_NONE)

	def register_handle(self):
		debug(self, "Fetching client register_info ...")

		# fetch the client register_info
		name = self._register_info_name
		co = self._get_handle.get(name, pyccn.Interest(publisherPublicKeyDigest = None))
		# Even if publisherPublicKeyDigest is None, we can also use it.
		if not co:
			debug(self, "Unable to fetch %s" % name)
			return False

		# self.reg_info_handle(co.content, co.signedInfo.publisherPublicKeyDigest)
		client_publicKey = co.content
		self.publish_data_key(client_publicKey)

		return True

	def reg_info_handle(self, reg_info, publicKeyID):
		if reg_info == publicKeyID:
			return True

	def publish_data_key(self, client_publicKey):
		dataKey_object = self.prepare_data_key_packet(client_publicKey)
		self.publisher.put(dataKey_object)

	def prepare_data_key_packet(self, client_publicKey):
		self._signed_info.ccn_data_dirty = True

		# data key need to be encrypted
		dec_dataKey = self.decrypt_dataKey(client_publicKey)

		co = pyccn.ContentObject(self._name_of_dataKey, dec_dataKey, self._signed_info)
		co.sign(self._key)
		print "the data key is : %s" % co.content
		print "the data key object name is : %s" % self._name_of_dataKey

		return co

	def decrypt_dataKey(self, client_publicKey):
		# now I cannot find how to encrypt the data key
		return self._data_key

def register(videosite):
	flag = videosite.register_handle()

	while flag == False:
		print "Fetching register_info ..."
		flag = videosite.register_handle()

if __name__ == '__main__':

	def usage():
		print("Usage: %s <uri>" % sys.argv[0])
		sys.exit(1)

	if (len(sys.argv) != 2):
		usage()

	uri = sys.argv[1]

	videosite = VideoSite(uri)
	videosite.run()

	# the threads need to be syncronised
	thread_loop = threading.Thread(name='gstLoop', target=videosite.run)
	thread_loop.start()

	thread_register = threading.Thread(name='register', target=register, args=(videosite, ))
	thread_register.start()
