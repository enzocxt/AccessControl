import pygtk
pygtk.require('2.0')
import pygst
pygst.require('0.10')

import gtk
import gst
import gobject

import sys, argparse, threading

import player, player_gui
import utils
from video_src import VideoSrc

import pyccn

class GstPlayer(player.GstPlayer):
	__pipeline = """
		queue2 name=video_input use-buffering=true max-size-time=500000000 ! decodebin2 ! %s
	""" % utils.video_sink

	def init_elements(self):
		self.vsrc = gst.element_factory_make("VideoSrc")
		self.player.add(self.vsrc)
		self.src = self.vsrc

	def on_status_update(self):
		video_status = self.vsrc.get_status()
		self.emit("status-updated", 
			"Video: %s\n"
			"Buffer: %d%% (playing: %s)" % (video_status, self.stats_buffering_percent, "Yes" if self.playing else "No"))
		return True

	def set_location(self, location):
		self.vsrc.set_property('location', location)
		video_input = self.player.get_by_name('video_input')
		self.vsrc.link(video_input)

class VideoClient():
	def __init__(self, cmd_args):
		freshness = 30 * 30

		self.window = player_gui.PlayerWindow(GstPlayer, cmd_args)
		self.cmd_args = cmd_args

		self.publisher = utils.RepoSocketPublisher()

		self._handle = pyccn.CCN()

		self._client_name = 'Alice'
		self._basename = pyccn.Name('/test/VideoSite/User')

		self._key = pyccn.CCN.getDefaultKey()
		
		# publish the public key by this name
		# '/test/VideoSite/User/Alice/Key'
		self._name_key = self._basename.append(self._client_name)
		self._name_key = self._name_key.append('Key')
#		self._signed_info = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._name_key), freshness = freshness)
#		self._singed_info_frames = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._name_key), freshness = 1)

		# publish the public key	
		signed_info = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._key), freshness = freshness)
		co = pyccn.ContentObject(self._name_key, self._key.publicToDER(), signed_info)
		co.sign(self._key)
		self.publisher.put(co)

		# publish the register info
		# '/test/VideoSite/User/Register_Info'
		self._register_info_name = self._basename.append('Register_Info')
		signed_info = pyccn.SignedInfo(self._key.publicKeyID, pyccn.KeyLocator(self._key), freshness = freshness)
		co = pyccn.ContentObject(self._register_info_name, self._key.publicToDER(), signed_info)
		co.sign(self._key)
		self.publisher.put(co)

	# play the video
	def run(self):
		gobject.threads_init()
		gtk.gdk.threads_init()

		self.window.load_file(self.cmd_args.URI)
		self.window.show_all()

def main(args):

	parser = argparse.ArgumentParser(description = 'Plays video stream.', add_help = False)
	parser.add_argument('--player-help', action="help", help = "show this help message and exit")
	parser.add_argument('-l', '--live', action="store_true", help = 'play in live mode')
	parser.add_argument('URI', help = 'URI of the video stream')

	cmd_args = parser.parse_args()	#parse the args from command line

	videoclient = VideoClient(cmd_args)
	videoclient.run()

#	thread_loop = threading.Thread(name='gstPlay', target=videoclient.run)
#	thread_loop.start()

	gtk.main()

if __name__ == '__main__':
	sys.exit(main(sys.argv))
