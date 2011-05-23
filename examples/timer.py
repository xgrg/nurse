#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

from nurse.base import *
from nurse.config import Config
from nurse.context import Context, ContextManager
from nurse.screen import *
from nurse.timer import *
from nurse.backends import *

class Incrementator(Object):
	def __init__(self):
		Object.__init__(self, 'default_name')

	def on_space_press(self, event):
		print "SPACE"
		if self.timer._state == 'PAUSED':
			self.timer.resume()
		elif self.timer._state == 'RUNNING':
			self.timer.pause()
		elif self.timer._state == 'INITIALIZED':
			self.timer.start()
		elif self.timer._state == 'RESUMING':
			self.timer.pause()
		elif self.timer._state == 'ENDED':
			self.timer.start()
		elif self.timer._state == 'STOPPED':
			self.timer.start()

	def on_enter_press(self, event):
		print 'ENTER'
		if self.timer._state in ['RUNNING', 'RESUMING']:
			self.timer.stop()
		elif self.timer._state in ['INITIALIZED', 'ENDED', 'STOPPED']:
			self.timer.start()

#-------------------------------------------------------------------------------
def main():
	Config.backend = 'pyglet'
	Config.init()

	#FIXME : find anoVther way to add the device
	context_manager = ContextManager()
	universe.context_manager = context_manager

	# manage context
	properties_all_active = { 'is_visible' : True, 'is_active' : True,
				'_is_receiving_events' : True} 
	context = Context('context', **properties_all_active)
	context_manager.add_state(context)
	context_manager.set_initial_state(context)
	context_manager.start()

	resolution = Config.resolution
	geometry = (0, 0, resolution[0], resolution[1])

	screen_fixed = VirtualScreenRealCoordinates('fixed screen', geometry)
	context.add_screen(screen_fixed)
	
	timer = PaceMaker("timer", 'INTERVAL', 5)

	incrementator = Incrementator()
	incrementator.context = context
	incrementator.timer = timer
	signal = (KeyBoardDevice.constants.KEYDOWN,
			KeyBoardDevice.constants.K_SPACE)
	context.connect(signal, incrementator, "on_space_press" )

	signal = (KeyBoardDevice.constants.KEYDOWN,
			KeyBoardDevice.constants.K_RETURN)
	context.connect(signal, incrementator, "on_enter_press" )
	# FPS
	event_loop = Config.get_event_loop()
	event_loop.start()

if __name__ == "__main__" : main()
