from base import *
import pyglet

''' This module is in charge of periodic events processing.
.. module:: timer
   :platform: Unix
         :synopsis: Timing and periodic events processing

	 .. moduleauthor:: Gregory Operto <gregory.operto@gmail.com>
	 '''


class TimeManager(Object):
    	''' 
    TimeManager manages and keeps tracks of the various possible concurrent 
    timing events/contexts. It deals with objects from the :class:`PaceMaker` 
    class which have a type (``ONCE``, ``INTERVAL``) and a specific 
    pace.
    	'''
	def __init__(self, name):
		Object.__init__ ( self, name )


	def register(self, pacemaker):		
		pass

	def unregister(self, pacemaker):
		pass


class PaceMaker(Object):
	''' 
    A :class:`PaceMaker` is defined by a name, a type (``ONCE``, ``INTERVAL``), 
    a specific pace. It has :func:`start`, :func:`stop`, :func:`pause`,
    :func:`resume` and :func:`tick` functions.

    The idea is that, depending on contexts being active or not, some timers can
    consequently get paused (e.g. if the game gets in pause mode, the game-related 
    timers should wait till the game is resumed)

    If the :class:`PaceMaker` is associated to a single-shot event (type ``ONCE``), 
    then the :func:`ring` function will get called. If the :class:`PaceMaker` 
    makes the pace for a periodic event (type ``INTERVAL``), then the :func:`tick` 
    function is called each ``_period``.

    .. warning::
    	``_start_time`` is not really the time at which the timer started since it
	is updated in case of pauses and resumes.

    :class:`PaceMaker` constructor
    Args:
    	name (str): Object name
        type (str): Type of timer, can be ``ONCE`` or ``INTERVAL``
        period (float): Timer period
    	'''

	def __init__(self, name, type, period):
		Object.__init__(self, name)
		self._type = type
		self._period = period
		self._start_time = 0
		self._pause_time = 0
		self._elapsed_time = 0
		self._state = 'INITIALIZED'

	def start(self):
		self._start_time = pyglet.clock.time.time()
		self._pause_time = 0
		self._elapsed_time = 0
		self._state = 'RUNNING'
		print self._state
		if self._type == 'ONCE':
			pyglet.clock.schedule_once(self.ring, self._period)
		elif self._type == 'INTERVAL':
			pyglet.clock.schedule_interval(self.tick, self._period)

	def tick(self, dt):
		'''
    A :func:`PaceMaker` of type ``INTERVAL`` ticks periodically. On the 
    opposite, a ``ONCE`` :func:`PaceMaker` rings when its time is over.
    		'''
		self._start_time = pyglet.clock.time.time()
		self._elapsed_time = 0 
		print self.name + ' ticking ' + str(dt)

	def ring(self, dt):
		'''
    A :func:`PaceMaker` of type ``ONCE`` rings when its time is over. On the 
    opposite, an ``INTERVAL`` :func:`PaceMaker` ticks periodically.
    		'''
		print self.name + ' ringing ' + str(dt)
		pyglet.clock.unschedule(self.ring)
		self._state = 'ENDED'
		print self._state

	def pause(self):
		if self._state not in ['RUNNING', 'RESUMING']:
			raise Exception('Timer paused while not running')
		self._pause_time = pyglet.clock.time.time()

		if self._type == 'ONCE':
			self._elapsed_time = self._elapsed_time + self._pause_time - self._start_time
			pyglet.clock.unschedule(self.ring)
		elif self._type == 'INTERVAL':
			self._elapsed_time = self._elapsed_time + self._pause_time - self._start_time
			if self._state == 'RESUMING':
				pyglet.clock.unschedule(self._finish_ongoing_interval)
			elif self._state == 'RUNNING':
				pyglet.clock.unschedule(self.tick)
		self._state = 'PAUSED'
		print self._state

	def _finish_ongoing_interval(self, dt):
		''' 
    When a periodic timer is paused in the middle of an interval, this last
    on-going interval must first finish before the timer can start ticking 
    again periodically.
		'''
		self.tick(dt)
		self._state = 'RUNNING'
		pyglet.clock.schedule_interval(self.tick, self._period)

	def resume(self):
		if self._state != 'PAUSED':
			raise Exception('Timer resumed while not paused')
		self._start_time = pyglet.clock.time.time()
		self._state = 'RESUMING'
		print self._state, self._period - self._elapsed_time
		if self._type == 'ONCE':
			pyglet.clock.schedule_once(self.ring, \
				self._period - self._elapsed_time)
		elif self._type == 'INTERVAL':
			# first finish the last ongoing interval
			pyglet.clock.schedule_once(self._finish_ongoing_interval, \
				self._period - self._elapsed_time)

			
	def stop(self):
		if self._type == 'ONCE' :
			pyglet.clock.unschedule(self.ring)
		if self._type == 'INTERVAL':
			if self._state == 'RESUMING':
				pyglet.clock.unschedule(self._finish_ongoing_interval)
			elif self._state == 'RUNNING':
				pyglet.clock.unschedule(self.tick)
		self._state = 'STOPPED'
		print self._state

