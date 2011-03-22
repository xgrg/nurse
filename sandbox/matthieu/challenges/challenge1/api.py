# -*- coding: iso-8859-15 -*-
import os, sys, uuid
import enum
import numpy as np
import pygame
import pyglet
from pyglet.gl import *


#-------------------------------------------------------------------------------
class Event(object): pass


class SignalEvent(Event):
	def __init__(self, sender, method, signal, signal_data=None):
		self.type = 'signal'
		self.sender = sender
		self.method = method
		self.signal = signal
		self.signal_data = signal_data

	def start(self):
		self.method(self)


#-------------------------------------------------------------------------------
class Object(object):
	def __init__(self, name):
		self.name = name
		self._sync_connections = {'__all__' : []}		
		self._async_connections = {'__all__' : []}		

	def set_property(self, name, value):
		self.__setattr__(name, value)

	def is_receiving_events(self):
		return True

	def connect(self, signal, receiver, slot="receive_events",
						asynchronous=True):
		'''
    mimic qt signal/slot connection

    signal:        any pickable object. If signal is equal to __all__ the slot
                   function will be called for any signal.
    receiver:      destination object.
    slot:          name of the function to call on the receiver.
    asynchronous:  true if the the slot is queued in the eventloop.
                   false if the slot is called directly during the emit call.
		'''
		connection = (receiver, slot)
		if asynchronous:
			connections = self._async_connections
		else:	connections = self._sync_connections
		connections.setdefault(signal, []).append(connection)

	def disconnect(self, signal, receiver, slot="receive_events",
						asynchronous=True):
		connection = (receiver, slot, asynchronous)
		connections = self._connections[signal]
		del connections[connections.index(connection)]

	def emit(self, signal, signal_data=None):
		try:
			async_connections = self._async_connections[signal]
		except KeyError:
			async_connections = []
		async_connections += self._async_connections['__all__']
		try:
			sync_connections = self._sync_connections[signal]
		except KeyError:
			sync_connections = []
		sync_connections += self._sync_connections['__all__']

		# batch active slots :
		#   done in 2 passes to avoid domino effect if some observers
		#   is_receiving_events status change after a first observer
		#   receive a signal.
		connections = [(receiver, slot) \
			for (receiver, slot) in sync_connections
			if receiver.is_receiving_events()]

		for (receiver, slot) in connections:
			method = receiver.__getattribute__(slot)
			event = SignalEvent(self, method, signal, signal_data)
			method(event)

		connections = [(receiver, slot) \
			for (receiver, slot) in async_connections
			if receiver.is_receiving_events()]

		event_loop = Config.get_event_loop_backend()
		for (receiver, slot) in connections:
			method = receiver.__getattribute__(slot)
			event = SignalEvent(self, method, signal, signal_data)
			event_loop.add_event(event)


universe = Object('universe')


#-------------------------------------------------------------------------------
class EventLoop(Object):
	def __init__(self, fps = 60.):
		Object.__init__(self, 'event_loop')
		self.fps = fps
		self._pending_events = []

	def add_event(self, event):
		self._pending_events.append(event)

	def get_events(self):
		try:
			yield self._pending_events.pop()
		except IndexError: pass


class SdlEventLoop(EventLoop):
	def __init__(self, fps = 60.):
		EventLoop.__init__(self, fps)

	def start(self):
		previous_time = pygame.time.get_ticks()

		while 1:
			self.read_events()
			time = pygame.time.get_ticks()
			dt = time - previous_time
			if dt < (1000. / self.fps): continue
			previous_time = time
			self.update(dt)

	def update(self, dt):
		universe.context_manager.display()
		universe.context_manager.update(dt)

	def read_events(self):
		if len(self._pending_events) != 0:
			e = self._pending_events.pop()
			e.start()
		Config.get_keyboard_backend().read_events()


class PygletEventLoop(EventLoop):
	def __init__(self, fps = 60.):
		EventLoop.__init__(self, fps)

	def start(self):
		pyglet.clock.schedule_interval(self.update, 1. / self.fps)
		pyglet.app.run()

	def update(self, dt):
		'''
    dt : delay in seconds between 2 calls of this method
                '''
		self.read_events()
		universe.context_manager.update(dt * 1000.)

	@classmethod
	def on_draw(cls):
		universe.context_manager.display()

	def read_events(self):
		if len(self._pending_events) != 0:
			e = self._pending_events.pop()
			e.start()

#-------------------------------------------------------------------------------
class KeyBoardDevice(Object):
	constants = enum.Enum(*(['KEYDOWN', 'KEYUP'] + \
		['K_' + chr(i) for i in range(ord('a'), ord('z') + 1)] + \
		['K_' + str(i) for i in range(10)] + \
		['K_UP', 'K_DOWN', 'K_LEFT', 'K_RIGHT', 'K_ESCAPE', 'K_SPACE']+\
		['UNKNOWN']))

	def __init__(self):
		Object.__init__(self, 'keyboard_device')

	@classmethod
	def _get_key_from_symbol(cls, symbol):
		try:
			return cls.keysym_map[symbol]
		except:
			print "warning: symbol '%d' is not handle" % symbol
			return cls.constants.UNKNOWN


class SdlKeyBoardDevice(KeyBoardDevice):
	keysym_map = {}
	for i in range(ord('a'), ord('z') + 1):
		key = 'K_' + chr(i)
		keysym_map[pygame.constants.__getattribute__(key)] = \
			KeyBoardDevice.constants.__getattribute__(key)
	for i in range(10):
		key = 'K_' + str(i)
		keysym_map[pygame.constants.__getattribute__(key)] = \
			KeyBoardDevice.constants.__getattribute__(key)
	for key in ['K_UP', 'K_DOWN', 'K_LEFT', 'K_RIGHT', 'K_ESCAPE',
		'K_SPACE', 'KEYDOWN', 'KEYUP']:
		keysym_map[pygame.constants.__getattribute__(key)] = \
			KeyBoardDevice.constants.__getattribute__(key)
	
	def __init__(self):
		KeyBoardDevice.__init__(self)

	def read_events(self):
		event = pygame.event.poll()
		if (event.type == 0): return
		keystate = pygame.key.get_pressed()
		if (event.type == pygame.constants.QUIT): sys.exit(0)
		if (event.type == pygame.constants.KEYDOWN):
			keymap = pygame.key.get_pressed()
			if keymap[pygame.constants.K_q] or \
				keymap[pygame.constants.K_ESCAPE]:
				sys.exit(0)
			elif keymap[pygame.constants.K_f]:
				pygame.display.toggle_fullscreen()
		# filter some events
		if event.type not in [pygame.constants.KEYDOWN,\
				pygame.constants.KEYUP]: return
		else:
			type = self._get_key_from_symbol(event.type)
			key = self._get_key_from_symbol(event.key)
			self.emit((type, key))


class PygletKeyBoardDevice(KeyBoardDevice):
	fullscreen = False
	keysym_map = {}
	for i in range(ord('a'), ord('z') + 1):
		key = chr(i)
		keysym_map[pyglet.window.key.__getattribute__(key.upper())] = \
			KeyBoardDevice.constants.__getattribute__('K_' + key)
	for i in range(10):
		key = str(i)
		keysym_map[pyglet.window.key.__getattribute__('NUM_' + key)] = \
			KeyBoardDevice.constants.__getattribute__('K_' + key)
	for key in ['UP', 'DOWN', 'LEFT', 'RIGHT', 'ESCAPE', 'SPACE']:
		keysym_map[pyglet.window.key.__getattribute__(key)] = \
			KeyBoardDevice.constants.__getattribute__('K_' + key)

	def __init__(self):
		KeyBoardDevice.__init__(self)
		self._win = None

	def attach_window(self, win):
		self._win = win
		self.on_key_press = win.event(self.on_key_press)
		self.on_key_release = win.event(self.on_key_release)

	def on_key_press(self, symbol, modifiers):
		if symbol == pyglet.window.key.ESCAPE or \
			symbol == pyglet.window.key.Q:
			sys.exit()
		elif symbol == pyglet.window.key.F:
			self._win.set_fullscreen(self.fullscreen)
			self.fullscreen = not self.fullscreen
		
		key = self._get_key_from_symbol(symbol)
		self.emit((KeyBoardDevice.constants.KEYDOWN, key))
		return pyglet.event.EVENT_HANDLED

	def on_key_release(self, symbol, modifiers):
		key = self._get_key_from_symbol(symbol)
		self.emit((KeyBoardDevice.constants.KEYUP, key))
		return pyglet.event.EVENT_HANDLED


#-------------------------------------------------------------------------------
class State(Object):
	def __init__(self, name):
		Object.__init__(self, name)
		self._fsm = None
		self._assign_properties = []
		self._transitions = {}

	def add_transition(self, sender, signal, state,
			src_prop={}, dst_prop={}, asynchronous=True):
		sender.connect(signal, self, "on_transition", asynchronous)
		self._transitions[signal] = (sender, state, src_prop, dst_prop)

	def assign_property(self, obj, name, value):
		self._assign_properties.append((obj, name, value))

	def remove_transition(self, transition):
		del self._transitions[transition]
		self._initial_state = state

	def is_receiving_events(self):
		return self._fsm._current_state == self

	# slots
	def on_entered(self):
		for (obj, name, value) in self._assign_properties:
			obj.set_property(name, value)
		self.emit("entered")

	def on_exited(self):
		self.emit("exited")

	def on_transition(self, event):
		sender, state, src_prop, dst_prop = \
			self._transitions[event.signal]
		self._fsm.change_state(self, state, src_prop, dst_prop)


class Context(State):
	def __init__(self, name, is_visible=True, is_active=True,
					_is_receiving_events=True):
		State.__init__(self, name)
		self._visible_data = {}
		self._screens = []
		self._fsm_list = []
		self.is_visible = is_visible
		self.is_active = is_active
		self._is_receiving_events = _is_receiving_events

	def add_fsm(self, fsm):
		self._fsm_list.append(fsm)

	def add_visible_data(self, data, layer=0):
		self._visible_data.setdefault(layer, []).append(data)

	def get_visible_data(self):
		return self._visible_data

	def add_screen(self, screen):
		self._screens.append(screen)

	def display(self):
		data = self.get_visible_data()
		for screen in self._screens:
			for layer, objects in data.items(): # from bg to fg
				for obj in objects:
					screen.display(obj)
	
	def update(self, dt):
		for fsm in self._fsm_list:
			fsm.update(dt)

	def delegate(self, event):
		self.emit(event.signal, event.signal_data)

	def is_receiving_events(self):
		return self._is_receiving_events


class StateMachine(State):
	START = 0
	STOP = 1
	def __init__(self, name='state machine', context=None):
		State.__init__(self, name)
		if context is None: context = Config.get_default_context()
		self._initial_state = None
		self._possible_states = {}
		self._current_state = None
		context.add_fsm(self)

	def set_initial_state(self, state):
		if state not in self._possible_states.values():
			raise ValueError('unknown initial state')
		self._initial_state = state

	def add_state(self, state):
		self._possible_states[state.name] = state
		state._fsm = self

	def change_state(self, src, dst, src_prop={}, dst_prop={}):
		if src != self._current_state: return
		if self._current_state is not None:
			self._current_state.on_exited()
		self._current_state = dst 
		if self._current_state is not None:
			self._current_state.on_entered()
		for k, v in src_prop.items(): src.set_property(k, v)
		for k, v in dst_prop.items(): dst.set_property(k, v)
		self.emit("state_changed", (src, dst))

	def start(self):
		if self._initial_state is None:
			default_state = State('__default__')
			self.add_state(default_state)
			self._initial_state = default_state
		self._current_state = self._initial_state
		self._current_state.on_entered()
		self.status = StateMachine.START
		self.emit("started")

	def stop(self):
		self.status = StateMachine.STOP
		self.emit("stopped")

	def is_receiving_events(self):
		return True

	# slots
	def on_entry(self):
		self.start()

	def on_exit(self):
		self.stop()


class ContextManager(StateMachine):
	def __init__(self):
		StateMachine.__init__(self, 'Context Manager')
		signal = '__all__'
		Config.get_keyboard_backend().connect(signal, self,
						asynchronous=False)

	def display(self):
		Config.get_graphic_backend().clean()
		for context in self._possible_states.values():
			if context.is_visible:
				context.display()
		Config.get_graphic_backend().flip()

	def update(self, dt):
		for context in self._possible_states.values():
			if context.is_active:
				context.update(dt)

	# slots
	def receive_events(self, event):
		# - try to modify the current context
		# - then notify observers
		try:
			self._current_state.on_transition(event)
		except KeyError:
			for context in self._possible_states.values():
				if context.is_receiving_events():
					context.delegate(event)



class Sprite(StateMachine):
	def __init__(self, name='sprite', context=None, layer=1, speed=100.):
		'''
    name:  name of the sprite
    layer: (default: 1 since 0 is reserved for background)
    speed: speed in world-coordinate metric per seconds
		'''
		StateMachine.__init__(self, name, context)
		if context is None: context = Config.get_default_context()
		context.add_visible_data(self, layer)
		self._current_frame_id = 0
		self._frames = {}
		self._frames_center_location = {}
		self._refresh_delay = {}
		self._location = np.zeros(2)
		self._speed = speed
		self._previous_time = pygame.time.get_ticks()

	def load_frames_from_filenames(self, state,
		frames_fnames=[], center_location=(0,0), fps=30):
		'''
    Load frames from images (one image per file) for a given state

    state:           A valid state of the Sprite State Machine.
                     If state equals __default__, these frames are used for
		     each state without any frames.
		     If frames_fnames is [] then no sprite is displayed for
		     the given state.
    frames_fnames:   liste of filenames.
    center_location: - tuple of coordinates in pixel from the bottom left corner
                       of the images (the same shift for all images).
		     - list of coordinates in pixel from the bottom left corner
		       of the images (one shift per image).
		  or - 'centered': the center is centered on the images.
		  or - 'centered_bottom': the center is centered on the bottom
		       of the images.
    fps:             number of frames per seconds.
		'''
		self._frames[state] = [ \
			Config.get_graphic_backend().load_image(fname) \
			for fname in frames_fnames]
		self._refresh_delay[state] = int(1000 / fps)
		loc = []
		if isinstance(center_location, str):
			if center_location == 'centered':
				for img in self._frames[state]:
					loc.append(np.array(img.get_size()) /2.)
			elif center_location == 'centered_bottom':
				for img in self._frames[state]:
					width, height = img.get_size()
					loc.append(np.array([width/2., height]))
		elif isinstance(center_location, list):
			loc = center_location
		else:	loc = [center_location] * len(self._frames[state])
		self._frames_center_location[state] = loc

	def get_frame_infos(self, time):
		'''
    Return frame infos for a given time : image uuid, center location
		'''
		state = self._current_state
		try:
			frames = self._frames[state]
		except KeyError:
			state = '__default__'
			frames = self._frames[state]
			if len(frames) == 0: return None, None
		refresh_delay = self._refresh_delay[state]
		frames_center_location = self._frames_center_location[state]
		frames_n = len(frames)
		id = int((time % (refresh_delay * frames_n)) / refresh_delay)
		return frames[id], frames_center_location[id]

	def update(self, dt):
		'''
    Update sprite location (in world coordinates) according to its
    control state and current active frame
		'''
		raise NotImplementedError

	def get_location(self):
		'''
    Return sprite location in world coordinate system
		'''
		return self._location

	def set_location(self, location):
		'''
    set sprite location in world coordinate system
		'''
		self._location = location


class MovingSprite(Sprite):
	Start_to_End = 0
	End_to_Start = 1
	def __init__(self, name='moving sprite', context=None,
					layer=2, speed=100.):
		'''
    path : list of world coordinates
		'''
		Sprite.__init__(self, name, context, layer, speed)
		if context is None: context = Config.get_default_context()
		self._path = None
		self._way = MovingSprite.Start_to_End
		self._indice_states = [\
			State("rest"), State("left"), State("left-up"),
			State("up"), State("right-up"),
			State("right"), State("right-down"),
			State("down"), State("left-down")]
		self._state_name_to_id = {"rest" : 0, "left" : 1, "left-up" : 2,
				'up' : 3, 'right-up' : 4, 'right' : 5,
				'right-down' : 6, 'down' : 7, 'left-down' : 8}
		for state in self._indice_states: self.add_state(state)
		self.set_initial_state(self._indice_states[0])
		self._checkpoint = 0
		self._directions = np.array([\
			[-1., -1., 0, 1., 1., 1., 0, -1.],
			[0, -1., -1., -1., 0, 1., 1., 1.]])
		self._directions /= np.sqrt((self._directions ** 2).sum(axis=0))

	def set_path(self, path):
		self._path = path
		self.set_current_state_from_path()
		self.set_initial_state(self._current_state)
		self.set_location(self._path[0])

	def get_next_checkpoint_id(self):
		if self._way == MovingSprite.Start_to_End:
			return (self._checkpoint + 1) % len(self._path)
		elif self._way == MovingSprite.End_to_Start:
			return (self._checkpoint + 1) % len(self._path)

	def set_current_state_from_path(self):
		p = self._checkpoint
		n = self.get_next_checkpoint_id()
		d = np.array(self._path[n]) - np.array(self._path[p])
		self._current_dir = d
		if np.abs(d).sum() == 0:
			state = 'rest'
		else:
			# FIXME : verifier qu'il n'y a pas d'inversion haut/bas
			dot = np.dot(d, self._directions)
			# (0, 0) direction has been removed
			id = np.argmax(dot) + 1
			state = self._indice_states[id]
		self.change_state(self._current_state, state)

	def update(self, dt):
		'''
    Update location and state of the sprite.

    dt : time since last update
		'''
		# FIXME: test if new_loc is available
		s = 1
		while s > 0:
			p = self._checkpoint
			n = self.get_next_checkpoint_id()
			state_name = self._current_state.name
			id = self._state_name_to_id[state_name]
			if id == 0: return
			delta = (self._directions.T[id - 1] * dt) * \
				self._speed / 1000.
			new_loc = self._location + delta
			s = np.dot(self._current_dir, new_loc - self._path[n])
			if s > 0:
				# distance already covered
				dist = np.sqrt(((self._location - \
						self._path[n]) ** 2).sum())
				self._location = self._path[n]
				self._checkpoint = n
				self.set_current_state_from_path()
				#remaining time to cover path during this update
				dt -= dist * 1000 / self._speed
		self._location = new_loc
		self.emit("location_changed", new_loc)


class Player(Sprite):
	def __init__(self, name='sprite', context=None,
				layer=2, speed=100.):
		Sprite.__init__(self, name, context, layer, speed)
		if context is None: context = Config.get_default_context()
		states = [State("rest"), State("left"), State("left-up"),
			State("up"), State("right-up"),
			State("right"), State("right-down"),
			State("down"), State("left-down")]
		for state in states: self.add_state(state)
		self.set_initial_state(states[0])

		# left
		signal = (KeyBoardDevice.constants.KEYDOWN,
				KeyBoardDevice.constants.K_LEFT)
		states[0].add_transition(context, signal, states[1])
		signal = (KeyBoardDevice.constants.KEYUP,
				KeyBoardDevice.constants.K_LEFT)
		states[1].add_transition(context, signal, states[0])

		# up
		signal = (KeyBoardDevice.constants.KEYDOWN,
				KeyBoardDevice.constants.K_UP)
		states[0].add_transition(context, signal, states[3])
		signal = (KeyBoardDevice.constants.KEYUP,
				KeyBoardDevice.constants.K_UP)
		states[3].add_transition(context, signal, states[0])

		# right
		signal = (KeyBoardDevice.constants.KEYDOWN,
				KeyBoardDevice.constants.K_RIGHT)
		states[0].add_transition(context, signal, states[5])
		signal = (KeyBoardDevice.constants.KEYUP,
				KeyBoardDevice.constants.K_RIGHT)
		states[5].add_transition(context, signal, states[0])

		# down
		signal = (KeyBoardDevice.constants.KEYDOWN,
				KeyBoardDevice.constants.K_DOWN)
		states[0].add_transition(context, signal, states[7])
		signal = (KeyBoardDevice.constants.KEYUP,
				KeyBoardDevice.constants.K_DOWN)
		states[7].add_transition(context, signal, states[0])

		# FIXME : add diagonal
		# FIXME : norm of diagonal moves must be equal to one
		self._delta_moves = np.array(\
			[[0, -1., -1., 0, 1., 1., 1., 0, -1.],
			[0, 0, -1., -1., -1., 0, 1., 1., 1.]]).T
		self._delta_moves *= self._speed
		self._state_name_to_id = {"rest" : 0, "left" : 1, "left-up" : 2,
				'up' : 3, 'right-up' : 4, 'right' : 5,
				'right-down' : 6, 'down' : 7, 'left-down' : 8}

	def update(self, dt):
		state_name = self._current_state.name
		# time = pygame.time.get_ticks()
		# delta = (time - self._previous_time)
		# f = float(delta) / universe._update_delay
		# self._previous_time = time
		if state_name == 'rest': return
		id = self._state_name_to_id[state_name]
		delta = (self._delta_moves[id] * dt / 1000.)
		# new_loc = self._location + self._delta_moves[id] * f
		new_loc = self._location + delta
		# FIXME: test if new_loc is available
		self._location = new_loc
		self.emit("location_changed", new_loc)


class StaticSprite(Sprite):
	def __init__(self, name, context, layer=0, imgname=None):
		Sprite.__init__(self, name, context, layer)
		self.load_frames_from_filenames('__default__',
					[imgname], 'centered', 1)

	def get_frame_infos(self, time):
		state = '__default__'
		frames = self._frames[state]
		frames_center_location = self._frames_center_location[state]
		return frames[0], frames_center_location[0]

	def update(self, dt):
		pass


class UniformLayer(Sprite):
	def __init__(self, name, context, layer=2, size=None,
			shift=(0, 0), color=(0, 0, 0), alpha=128):
		Sprite.__init__(self, name, context, layer)
		gfx = Config.get_graphic_backend()
		self._surface = gfx.get_uniform_surface(shift, size,
							color, alpha)
		self._center = np.array(self._surface.get_size()) /2.
		Sprite.set_location(self, np.array(shift) + self._center)
	
	def get_frame_infos(self, time):
		return self._surface, self._center

	def update(self, dt):
		pass


class DialogState(State):
	def __init__(self, name='text', text='...', font='Times New Roman',
		font_size=20, max_width=100, max_lines=3, perso=None,
		char_per_sec=5., writing_machine_mode=True):
		State.__init__(self, name)
		self._text = text
		self.font = font
		self.font_size = font_size
		self.max_width = max_width
		self.max_lines = max_lines
		self.perso = perso
		if writing_machine_mode:
			self.char_delay = 1000. / char_per_sec
		else:	self.char_delay = 0
		self.writing_machine_mode = writing_machine_mode
		self.list_backend_repr = []
		self._current_time = 0
		self._current_indice = 0
		self._current_text = ''
		self._current_height = 0
	
	def _update_chars(self, n):
		max_ind = len(self._text)
		ind = self._current_indice
		if ind == max_ind: return
		new_ind = ind + n
		if new_ind > max_ind: new_ind = max_ind
		new_text = self._text[ind:new_ind]
		self._current_text += new_text
		self._current_indice = new_ind
		anchor_x, anchor_y = self._fsm.get_location()
		repr = Config.get_graphic_backend().load_text(\
				self._current_text, self.font, self.font_size,
				anchor_x, anchor_y + self._current_height)
		if repr.content_width <= self.max_width:
			if len(self.list_backend_repr) == 0:
				self.list_backend_repr.append(repr)
			else:	self.list_backend_repr[-1] = repr
		else:
			self._current_height += repr.content_height
			repr = Config.get_graphic_backend().load_text(\
				new_text, self.font, self.font_size,
				anchor_x, anchor_y + self._current_height)
			self.list_backend_repr.append(repr)
			self._current_text = new_text
			if len(self.list_backend_repr) > self.max_lines:
				del self.list_backend_repr[0]
				Config.get_graphic_backend().shift_text(self,
							repr.content_height)
				self._current_height -= repr.content_height
				
	def update(self, dt):
		self._current_time += dt	
		if self._current_time >= self.char_delay:
			if self.char_delay == 0:
				n = len(self._text)
			else:	n = int(self._current_time / self.char_delay)
			self._update_chars(n)
			self._current_time -= n * self.char_delay
		


class Dialog(Sprite):
	def __init__(self, name='dialog', context=None, layer=2):
		Sprite.__init__(self, name, context, layer)

	def update(self, dt):
		self._current_state.update(dt)


class Text(Sprite):
	def __init__(self, name='text', context=None, layer=2,
		text='...', font='Times New Roman', font_size=20):
		Sprite.__init__(self, name, context, layer)
		self.text = text
		self.font = font
		self.font_size = font_size
		self.backend_repr = None

	def update(self, dt): #FIXME : on devrait pas avoir a updater le dialog?
		self.backend_repr = Config.get_graphic_backend().load_text(\
				self.text, self.font, self.font_size,
				self._location[0], self._location[1])


class FpsSprite(Sprite):
	'''Compute and display current FPS (Frames per second) rate.'''
	def __init__(self, name='fps', context=None, layer=3,
		fg_color=(255, 255, 255), bg_color=(0, 0, 0)):
		Sprite.__init__(self, name, context, layer)
		if context is None: context = Config.get_default_context()
		self.fg_color = fg_color
		self.bg_color = bg_color

	def update(self, dt):
		pass

#-------------------------------------------------------------------------------
class ImageProxy(object):
	def __init__(self, raw_image):
		self._raw_image = raw_image

	def get_raw_image(self):
		return self._raw_image


class SdlImageProxy(ImageProxy):
	def __init__(self, raw_image):
		ImageProxy.__init__(self, raw_image)

	def get_size(self):
		return self._raw_image.get_size()

	def get_width(self):
		return self._raw_image.get_size()[0]

	def get_height(self):
		return self._raw_image.get_size()[1]


class PygletImageProxy(ImageProxy):
	def __init__(self, raw_image):
		ImageProxy.__init__(self, raw_image)

	def get_size(self):
		if self._raw_image is None: return 0, 0 #FIXME
		return self._raw_image.width, self._raw_image.height

	def get_width(self):
		return self._raw_image.width

	def get_height(self):
		return self._raw_image.height


#-------------------------------------------------------------------------------
class GraphicBackend(object):
	# GraphicBackend and derivated classes are singletons
	instances = {}

	def __new__(cls, *args, **kwargs):
		if GraphicBackend.instances.get(cls) is None:
			GraphicBackend.instances[cls] = object.__new__(cls)
		return GraphicBackend.instances[cls]

	def display(self, screen, obj):
		if isinstance(obj, FpsSprite):
			type = 'fps'
		elif isinstance(obj, Dialog):
			type = 'dialog'
		elif isinstance(obj, Text):
			type = 'text'
		elif isinstance(obj, Sprite):
			type = 'sprite'
		else:	type = None
		self.display_map[type](self, screen, obj)

	def display_sprite(self, screen, sprite):
		time = pygame.time.get_ticks()
		frame_proxy, center = sprite.get_frame_infos(time)
		if frame_proxy is None: return
		raw_img = frame_proxy.get_raw_image()
		dst_pos = screen.get_ref() + sprite.get_location() - center
		src_rect = None # FIXME : clip the area to blit
		return (raw_img, dst_pos, src_rect)

	def flip(self):
		raise NotImplementedError

	def clean(self):
		raise NotImplementedError

	def load_text(self, text, font='Times New Roman',
				font_size=20, x=0, y=0):
		raise NotImplementedError

	def load_image(self, filename):
		raise NotImplementedError

	def load_image(self, filename):	
		raise NotImplementedError

	def get_uniform_surface(self, shift=(0, 0), size=None,
				color=(0, 0, 0), alpha=128):
		raise NotImplementedError


class SdlGraphicBackend(GraphicBackend):
	display_map = {}

	def __init__(self, resolution, flags):
		GraphicBackend.__init__(self)
		pygame.init()
		pygame.font.init()
		self._screen = pygame.display.set_mode(resolution, flags)
		self._clock = pygame.time.Clock()
		self._font = pygame.font.Font(None, 40)
		self._img_path = 'pix'

	def display_sprite(self, screen, sprite):
		res = GraphicBackend.display_sprite(self, screen, sprite)
		self._screen.blit(*res)

	def display_dialog(self, screen, dialog):
		# FIXME
		pass

	def display_text(self, screen, text):
		# FIXME
		pass

	def display_fps(self, screen, fps):
		self._clock.tick()
		true_fps = self._clock.get_fps()
		text = self._font.render(str(true_fps), True,
			fps.fg_color, fps.bg_color)
		self._screen.blit(text, fps.get_location())

	def flip(self):
		pygame.display.flip()

	def clean(self):
		self._screen.fill((0, 0, 0))

	def get_uniform_surface(self, shift=(0, 0), size=None,
				color=(0, 0, 0), alpha=128):
		if size is not None:
			flags = self._screen.get_flags()
			surface = pygame.Surface(size, flags)
		else:	surface = self._screen.convert()
		surface.fill(color)
		surface.set_alpha(alpha)
		return SdlImageProxy(surface)

	def load_image(self, filename):
		surface = pygame.image.load(os.path.join(self._img_path,
							filename))
		alpha_color = (0xff, 0, 0xff)
		flags = pygame.constants.SRCCOLORKEY | pygame.constants.RLEACCEL
		surface.set_colorkey(alpha_color, flags)
		return SdlImageProxy(surface)

	def load_text(self, text, font='Times New Roman',
				font_size=20, x=0, y=0):
		return None #FIXME

	def get_screen(self):
		return SdlImageProxy(self._screen)
	

SdlGraphicBackend.display_map.update({ \
	'sprite' : SdlGraphicBackend.display_sprite,
	'dialog' : SdlGraphicBackend.display_dialog,
	'text' : SdlGraphicBackend.display_text,
	'fps' : SdlGraphicBackend.display_fps})


class PygletGraphicBackend(GraphicBackend):
	display_map = {}
	
	def __init__(self, resolution, caption):
		GraphicBackend.__init__(self)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		pyglet.resource.path.append('pix')
		pyglet.resource.reindex()
		self._win = pyglet.window.Window(resolution[0], resolution[1],
							caption=caption)
		self._fps_display = pyglet.clock.ClockDisplay()

	def _invert_y_axis(self, img_height, pos_y):
		return self._win.height - pos_y - img_height

	def display_sprite(self, screen, sprite):
		sprite, dst_pos, src_rect = GraphicBackend.display_sprite(self,
							screen, sprite)
		dst_pos[1] = self._invert_y_axis(sprite.height, dst_pos[1])
		sprite.set_position(*dst_pos)
		sprite.draw()
		# FIXME use src_rect

	def display_dialog(self, screen, dialog):
		repr_list = dialog._current_state.list_backend_repr
		for repr in repr_list: repr.draw()

	def display_text(self, screen, text):
		repr = text.backend_repr
		if repr is not None: repr.draw()

	def display_fps(self, screen, fps):
		pos = list(fps.get_location())
		pos[1] = self._invert_y_axis(self._fps_display.label.height,
								pos[1])
		self._fps_display.label.x = pos[0]
		self._fps_display.label.y = pos[1]
		self._fps_display.draw()

	def flip(self):
		pass # nothing to do

	def clean(self):
		self._win.clear()

	def get_uniform_surface(self, shift=(0, 0), size=None,
				color=(0, 0, 0), alpha=128):
		if size is None: size = self._win.width, self._win.height
		surface = PygletUniformSurface(shift, size, color, alpha)
		return PygletImageProxy(surface)

	def load_image(self, filename):
		img = pyglet.resource.image(filename)
		sprite = pyglet.sprite.Sprite(img, 0, 0)
		return PygletImageProxy(sprite)

	def load_text(self, text, font='Times New Roman',
				font_size=20, x=0, y=0):
		label = pyglet.text.Label(text, font_name=font,
				font_size=font_size, x=x, y=y)
		label.y = self._invert_y_axis(label.content_height, y)
		return label

	def shift_text(self, text, shift):
		repr_list = text.list_backend_repr
		for repr in repr_list: repr.y += shift
			
	def get_screen(self):
		return SdlImageProxy(self._win)
	

PygletGraphicBackend.display_map.update({ \
	'sprite' : PygletGraphicBackend.display_sprite,
	'dialog' : PygletGraphicBackend.display_dialog,
	'text' : PygletGraphicBackend.display_text,
	'fps' : PygletGraphicBackend.display_fps})



class PygletUniformSurface(object):
	def __init__(self, shift, size, color, alpha):
		self._x, self._y = int(shift[0]), int(shift[1])
		self.width = int(size[0])
		self.height = int(size[1])
		x2, y2 = self.width, self.height
		self._batch = pyglet.graphics.Batch()
		self._batch.add(4, pyglet.gl.GL_QUADS, None,
			('v2i', [0, 0, x2, 0, x2, y2, 0, y2]),
			('c4B', (list(color) + [int(alpha)]) * 4))

	def set_position(self, x, y):
		self._x = x
		self._y = y

	def draw(self):
		glPushMatrix()
		glTranslatef(self._x, self._y, 0)
		glEnable(GL_BLEND)
		self._batch.draw()
		glDisable(GL_BLEND)
		glPopMatrix()


#-------------------------------------------------------------------------------
class VirtualScreen(Object):
	def __init__(self, name, geometry=(0, 0, 320, 200)):
		self._x, self._y, self._width, self._height = geometry

	def display(self, obj):
		Config.get_graphic_backend().display(self, obj)

	def get_ref(self):
		'''
    Return the referential coordinates (top-left corner of the virtual screen
    defined in real screen pixel coordinates).
		'''
		return self._ref_center



class VirtualScreenWorldCoordinates(VirtualScreen):
	def __init__(self, name='default_screen', geometry=(0, 0, 320, 200),
				focus=np.array([0, 0]), focus_on=None):
		'''
    name:       name of the screen
    geometry:   geometry of the screen: tuple (x, y, w, h):
                x: x position of the bottom left border in screen coordinates
                y: y position of the bottom left border in screen coordinates
                w: width of the screen in pixels
                h: height of the screen in pixels
    focus:      position in world coordinates on which the screen is focused
                (center of the screen).
    focus_on:   follow location of the given object (call get_location() func).
		'''
		VirtualScreen.__init__(self, name, geometry)
		self.set_focus(focus)
		if focus_on is not None:
			focus_on.connect("location_changed", self,
				"on_focus_changed", asynchronous=False)
		self.dst_pos = None

	def set_focus(self, focus):
		self._ref_center = np.array([self._x + self._width / 2,
					self._y + self._height / 2]) - focus
		self._focus = focus

	def on_focus_changed(self, event):
		location = event.signal_data
		self.set_focus(location)


class VirtualScreenRealCoordinates(VirtualScreen):
	def __init__(self, name='default_screen_real_coords',
			geometry=(0, 0, 320, 200)):
		VirtualScreen.__init__(self, name, geometry)
		self._ref_center = np.array([self._x, self._y])


#-------------------------------------------------------------------------------
class Config(object):
	# config data values
	graphic_backend = 'sdl'
	event_loop_backend = 'sdl'
	keyboard_backend = 'sdl'
	resolution = 800, 600
	caption = 'nurse game engine'
	sdl_flags = pygame.constants.DOUBLEBUF | pygame.constants.HWSURFACE | \
				pygame.constants.HWACCEL # | pygame.FULLSCREEN  
	fps = 60

	# internal data
	default_context = Context('default')
	graphic_backend_map = {\
		'sdl' : (SdlGraphicBackend, (resolution, sdl_flags)),
		'pyglet' : (PygletGraphicBackend, (resolution, caption))}
	event_loop_backend_map = {'sdl' : SdlEventLoop,
				'pyglet' : PygletEventLoop}
	keyboard_backend_map = {'sdl' : SdlKeyBoardDevice,
				'pyglet' : PygletKeyBoardDevice}
	graphic_backend_instance =  None
	event_loop_backend_instance = None
	keyboard_backend_instance = None
	# FIXME : add devices (keyboard, mouse) backend

	@classmethod
	def init(cls):
		# instanciate backends
		Config.get_graphic_backend()
		Config.get_event_loop_backend()

	@classmethod
	def read_config_file(cls):
		pass # FIXME : read from file (configobj ?)

	@classmethod
	def get_default_context(cls):
		return Config.default_context

	@classmethod
	def get_graphic_backend(cls):
		if cls.graphic_backend_instance is None:
			c, args = cls.graphic_backend_map[cls.graphic_backend]
			cls.graphic_backend_instance = c(*args)
		return cls.graphic_backend_instance

	@classmethod
	def get_event_loop_backend(cls):
		if cls.event_loop_backend_instance is None:
			c = cls.event_loop_backend_map[cls.event_loop_backend]
			cls.event_loop_backend_instance = c(Config.fps)
			if cls.event_loop_backend == 'pyglet':
				gfx = cls.get_graphic_backend()
				win = gfx.get_screen().get_raw_image()
				instance = cls.event_loop_backend_instance
				instance.on_draw = win.event(instance.on_draw)
		return cls.event_loop_backend_instance

	@classmethod
	def get_keyboard_backend(cls):
		if cls.keyboard_backend_instance is None:
			c = cls.keyboard_backend_map[cls.keyboard_backend]
			cls.keyboard_backend_instance = c()
			if cls.keyboard_backend == 'pyglet':
				gfx = cls.get_graphic_backend()
				win = gfx.get_screen().get_raw_image()
				instance = cls.keyboard_backend_instance
				instance.attach_window(win)
		return cls.keyboard_backend_instance