import sys
import time
import timeit
import numpy as np
import numpy.random as rdn
import OpenGL.GL as gl
# import OpenGL.GLUT as glut
from python_qt_binding import QtCore, QtGui
from python_qt_binding.QtCore import Qt, pyqtSignal
from python_qt_binding.QtOpenGL import QGLWidget, QGLFormat
from interactionevents import InteractionEvents as events
from useractions import UserActions as actions
from useractions import UserActionGenerator
import bindingmanager
from debugtools import DEBUG, log_debug, log_info, log_warn
import interactionmanager
import paintmanager
from tools import FpsCounter, show_window
import cursors

__all__ = [
'GalryWidget',
'GalryTimerWidget',
'AutodestructibleWindow',
'create_custom_widget',
'create_basic_window',
'show_basic_window',
]

# # DEBUG: raise errors if Numpy arrays are unnecessarily copied
# from OpenGL.arrays import numpymodule
# try:
    # numpymodule.NumpyHandler.ERROR_ON_COPY = True
# except Exception as e:
    # print "WARNING: unable to set the Numpy-OpenGL copy warning"

# Set to True or to a number of milliseconds to have all windows automatically
# killed after a fixed time. It is useful for automatic debugging or
# benchmarking.
AUTODESTRUCT = False
DEFAULT_AUTODESTRUCT = 1000

# Display the FPS or not.
DISPLAY_FPS = DEBUG == True

# Default manager classes.
DEFAULT_MANAGERS = dict(
    paint_manager=paintmanager.PaintManager,
    binding_manager=bindingmanager.BindingManager,
    interaction_manager=interactionmanager.InteractionManager,
)



# Main Galry class.
class GalryWidget(QGLWidget):
    """Efficient interactive 2D visualization widget.
    
    This QT widget is based on OpenGL and depends on both PyQT (or PySide)
    and PyOpenGL. It implements low-level mechanisms for interaction processing
    and acts as a glue between the different managers (PaintManager, 
    BindingManager, InteractionManager).
    
    """
    # background color as a 4-tuple (R,G,B,A)
    bgcolor = (0, 0, 0, 0)
    autosave = None
    
    # default window size
    width, height = 600, 600
    
    # FPS counter, used for debugging
    fps_counter = FpsCounter()
    display_fps = DISPLAY_FPS

    # widget creation parameters
    bindings = None
    companion_classes_initialized = False
    
    # constrain width/height ratio when resizing of zooming
    constrain_ratio = False
    constrain_navigation = False
    
    # Initialization methods
    # ----------------------
    def __init__(self, format=None, autosave=None, getfocus=True, **kwargs):
        """Constructor. Call `initialize` and initialize the companion classes
        as well."""
        super(GalryWidget, self).__init__(format)
        
        self.initialized = False
        
        # Load the QT curors here, after QT has been initialized.
        cursors.load()
        
        # Capture keyboard events.
        if getfocus:
            self.setFocusPolicy(Qt.WheelFocus)
        
        # Capture mouse events.
        self.setMouseTracking(True)
        
        # Initialize the objects providing the core features of the widget.
        self.user_action_generator = UserActionGenerator()
        
        self.is_fullscreen = False
        
        self.events_to_signals = {}
        self.prev_event = None
                                    
        # keyword arguments without "_manager" => passed to initialize                  
        self.initialize(**kwargs)

        # initialize companion classes if it has not been done in initialize
        if not self.companion_classes_initialized:
            self.initialize_companion_classes()
        self.initialize_bindings()
        
        # update rendering options
        self.paint_manager.set_rendering_options(
                        constrain_ratio=self.constrain_ratio,
                        )
        self.interaction_manager.constrain_navigation = self.constrain_navigation
        
        self.autosave = autosave
        
    def set_bindings(self, *bindings):
        """Set the interaction mode by specifying the binding object.
        
        Several binding objects can be given for the binding manager, such that
        the first one is the currently active one.
        
        Arguments:
          * bindings: a list of classes instances deriving from
            BindingSet.
            
        """
        bindings = list(bindings)
        if not bindings:
            bindings = [bindingmanager.DefaultBindingSet()]
        # if type(bindings) is not list and type(bindings) is not tuple:
            # bindings = [bindings]
        # if binding is a class, try instanciating it
        for i in xrange(len(bindings)):
            if not isinstance(bindings[i], bindingmanager.BindingSet):
                bindings[i] = bindings[i]()
        self.bindings = bindings
        
    def set_companion_classes(self, **kwargs):
        """Set specified companion classes, unspecified ones are set to
        default classes.
        
        Arguments:
          * **kwargs: the naming convention is: `paint_manager=PaintManager`.
            The key `paint_manager` is the name the manager is accessed from 
            this widget and from all other companion classes. The value
            is the name of the class, it should end with `Manager`.
        
        """
        if not hasattr(self, "companion_classes"):
            self.companion_classes = {}
            
        self.companion_classes.update(kwargs)
        
        # default companion classes
        self.companion_classes.update([(k,v) for k,v in \
            DEFAULT_MANAGERS.iteritems() if k not in self.companion_classes])
        
    def initialize_bindings(self):
        """Initialize the interaction bindings."""
        if self.bindings is None:
            self.set_bindings()
        self.binding_manager.add(*self.bindings)
        
        # set base cursor: the current binding is the first one
        self.interaction_manager.base_cursor = self.bindings[0].base_cursor
        
    def initialize_companion_classes(self):
        """Initialize companion classes."""
        # default companion classes
        if not getattr(self, "companion_classes", None):
            self.set_companion_classes()
        
        # create the managers
        for key, val in self.companion_classes.iteritems():
            log_debug("Initializing '%s'" % key)
            obj = val(self)
            setattr(self, key, obj)
        
        # link all managers
        for key, val in self.companion_classes.iteritems():
            for child_key, child_val in self.companion_classes.iteritems():
                if child_key == key:
                    continue
                obj = getattr(self, key)
                setattr(obj, child_key, getattr(self, child_key))
        
        self.interaction_manager.constrain_navigation = self.constrain_navigation        
        self.companion_classes_initialized = True
        
    def initialize(self, **kwargs):
        """Initialize the widget.
        
        Parameters such as bindings, companion_classes can be
        set here, by overriding this method. If initializations must be done
        after companion classes instanciation, then
        self.initialize_companion_classes can be called here.
        Otherwise, it will be called automatically after initialize().
        
        """
        pass
        
    def clear(self):
        """Clear the view."""
        self.paint_manager.reset()
        
    def reinit(self):
        """Reinitialize OpenGL.
        
        The clear method should be called before.
        
        """
        self.initializeGL()
        self.resizeGL(self.width, self.height)
        self.updateGL()
        
        
    # OpenGL widget methods
    # ---------------------
    def initializeGL(self):
        """Initialize OpenGL parameters."""
        self.paint_manager.initializeGL()
        self.initialized = True
        
    def paintGL(self):
        """Paint the scene.
        
        Called as soon as the window needs to be painted (e.g. call to 
        `updateGL()`).
        
        This method calls the `paint_all` method of the PaintManager.
        
        """
        # paint fps
        if self.display_fps:
            self.paint_fps()
        # paint everything
        self.paint_manager.paintGL()
        # flush GL commands
        gl.glFlush()
        # compute FPS
        self.fps_counter.tick()
        if self.autosave:
            self.save_image(self.autosave)
        
    def paint_fps(self):
        """Display the FPS on the top-left of the screen."""
        self.paint_manager.update_fps(int(self.fps_counter.get_fps()))
        
    def resizeGL(self, width, height):
        self.width, self.height = width, height
        self.paint_manager.resizeGL(width, height)
        
    def sizeHint(self):
        return QtCore.QSize(self.width, self.height)
        
        
    # Event methods
    # -------------
    def mousePressEvent(self, e):
        self.user_action_generator.mousePressEvent(e)
        self.process_interaction()
        
    def mouseReleaseEvent(self, e):
        self.user_action_generator.mouseReleaseEvent(e)
        self.process_interaction()
        
    def mouseDoubleClickEvent(self, e):
        self.user_action_generator.mouseDoubleClickEvent(e)
        self.process_interaction()
        
    def mouseMoveEvent(self, e):
        self.user_action_generator.mouseMoveEvent(e)
        self.process_interaction()
        
    def keyPressEvent(self, e):
        self.user_action_generator.keyPressEvent(e)
        self.process_interaction()
        
    def keyReleaseEvent(self, e):
        self.user_action_generator.keyReleaseEvent(e)
        
    def wheelEvent(self, e):
        self.user_action_generator.wheelEvent(e)
        self.process_interaction()
        
        
    # Normalization methods
    # ---------------------
    def normalize_position(self, x, y):
        """Window coordinates ==> world coordinates."""
        if not hasattr(self.paint_manager, 'renderer'):
            return None
        vx, vy = self.paint_manager.renderer.viewport
        x = -vx + 2 * vx * x / float(self.width)
        y = -(-vy + 2 * vy * y / float(self.height))
        return x, y
             
    def normalize_diff_position(self, x, y):
        """Normalize the coordinates of a difference vector between two
        points.
        """
        if not hasattr(self.paint_manager, 'renderer'):
            return None
        vx, vy = self.paint_manager.renderer.viewport
        x = 2 * vx * x/float(self.width)
        y = -2 * vy * y/float(self.height)
        return x, y
        
    def normalize_action_parameters(self, parameters):
        """Normalize points in the action parameters object in the window
        coordinate system.
        
        Arguments:
          * parameters: the action parameters object, containing all
            variables related to user actions.
            
        Returns:
           * parameters: the updated parameters object with normalized
             coordinates.
             
        """
        parameters["mouse_position"] = self.normalize_position(\
                                                *parameters["mouse_position"])
        parameters["mouse_position_diff"] = self.normalize_diff_position(\
                                            *parameters["mouse_position_diff"])
        parameters["mouse_press_position"] = self.normalize_position(\
                                            *parameters["mouse_press_position"])
        return parameters
    
    
    # Signal methods
    # --------------
    def connect_events(self, arg1, arg2):
        """Makes a connection between a QT signal and an interaction event.
        
        The signal parameters must correspond to the event parameters.
        
        Arguments:
          * arg1: a QT bound signal or an interaction event.
          * arg2: an interaction event or a QT bound signal.
        
        """
        if type(arg1) == int or type(arg1) == str:
            self.connect_event_to_signal(arg1, arg2)
        elif type(arg2) == int or type(arg2) == str:
            self.connect_signal_to_event(arg1, arg2)
        # else:
            # raise TypeError("One of the arguments must be an InteractionEvents \
               # enum value")
    
    def connect_signal_to_event(self, signal, event):
        """Connect a QT signal to an interaction event.
        
        The event parameters correspond to the signal parameters.
        
        Arguments:
          * signal: a QT signal.
          * event: an InteractionEvent enum value.
        
        """
        if signal is None:
            raise Exception("The signal %s is not defined" % signal)
        slot = lambda *args, **kwargs: \
                self.process_interaction(event, args, **kwargs)
        signal.connect(slot)
        
    def connect_event_to_signal(self, event, signal):
        """Connect an interaction event to a QT signal.
        
        The event parameters correspond to the signal parameters.
        
        Arguments:
          * event: an InteractionEvent enum value.
          * signal: a QT signal.
        
        """
        self.events_to_signals[event] = signal
        
        
    # Interaction methods
    # -------------------
    def switch_interaction_mode(self):
        """Switch the interaction mode."""
        binding = self.binding_manager.switch()
        # set base cursor
        self.interaction_manager.base_cursor = binding.base_cursor
        return binding
    
    def set_interaction_mode(self, mode):
        """Set the interaction mode.
        
        Arguments:
          * mode: either a class deriving from `BindingSet` and which has been
            specified in `set_bindings`, or directly a `BindingSet` instance.
        
        """
        binding = self.binding_manager.set(mode)
        # set base cursor
        self.interaction_manager.base_cursor = binding.base_cursor
        return binding
        
    def get_current_action(self):
        """Return the current user action with the action parameters."""
        # get current action
        action = self.user_action_generator.action
        
        # get current key if the action was KeyPressAction
        key = self.user_action_generator.key
        
        # get key modifier
        key_modifier = self.user_action_generator.key_modifier
        
        # retrieve action parameters and normalize using the window size
        parameters = self.normalize_action_parameters(
                        self.user_action_generator.get_action_parameters())
            
        return action, key, key_modifier, parameters
        
    def get_current_event(self):
        """Return the current interaction event corresponding to the current
        user action."""
        # get the current interaction mode
        binding = self.binding_manager.get()
        
        # get current user action
        action, key, key_modifier, parameters = self.get_current_action()
        
        # get the associated interaction event
        event, param_getter = binding.get(action, key=key,
                                                  key_modifier=key_modifier)
        
        # get the parameter object by calling the param getter
        if param_getter is not None:
            args = param_getter(parameters)
        else:
            args = None
            
        return event, args
        
    def process_interaction(self, event=None, args=None):
        """Process user interaction.
        
        This method is called after each user action (mouse, keyboard...).
        It finds the right action associated to the command, then the event 
        associated to that action.
        
        Arguments:
          * event=None: if None, the current event associated to the current
            user action is retrieved. Otherwise, an event can be directly
            passed here to force the trigger of any interaction event.
          * args=None: the arguments of the event if event is not None.
        
        """
        if event is None:
            # get current event from current user action
            event, args = self.get_current_event()
        
        # handle interaction mode change
        if event == events.SwitchInteractionModeEvent:
            binding = self.switch_interaction_mode()
            log_info("Switching interaction mode to %s." % \
                binding.__class__.__name__)
        
        # process the interaction event
        self.interaction_manager.process_event(event, args)
        
        # raise a signal if there is one associated to the current event
        if event in self.events_to_signals:
            self.events_to_signals[event].emit(*args)
        
        # set cursor
        self.setCursor(self.interaction_manager.get_cursor())
        
        # clean current action (unique usage)
        self.user_action_generator.clean_action()
        
        # update the OpenGL view
        if not isinstance(self, GalryTimerWidget) and (event is not None or self.prev_event is not None):
            self.updateGL()
            
        # keep track of the previous event
        self.prev_event = event
    
    
    # Miscellaneous
    # -------------
    def save_image(self, file=None):
        """Save a screenshot of the widget in the specified file."""
        if file is None:
            file = "image.png"
        image = self.grabFrameBuffer()
        image.save(file,"PNG")
    
    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            if hasattr(self.window, 'showFullScreen'):
                self.window.showFullScreen()
        else:
            if hasattr(self.window, 'showNormal'):
                self.window.showNormal()
    
    
    # Focus methods
    # -------------
    def focusOutEvent(self, event):
        self.user_action_generator.focusOutEvent(event)
    
    
        
class GalryTimerWidget(GalryWidget):
    timer = None
    
    """Special widget with periodic timer used to update the scene at 
    regular intervals."""
    def initialize_timer(self, dt=1.):
        """Initialize the timer.
        
        This method *must* be called in the `initialize` method of the widget.
        
        Arguments:
          * dt=1.: the timer interval in seconds.
          
        """
        self.t = 0.
        self.dt = dt
        self.t0 = timeit.default_timer()
        # start simulation after initialization completes
        self.timer = QtCore.QTimer()
        self.timer.setInterval(dt * 1000)
        self.timer.timeout.connect(self.update_callback)
        self.paint_manager.t = self.t
        
    def update_callback(self):
        """Callback function for the timer.
        
        Calls `paint_manager.update_callback`, so this latter method should be 
        implemented in the paint manager. The attribute `self.t` is 
        available here and in the paint manager.
        
        """
        self.t = timeit.default_timer() - self.t0
        if hasattr(self.paint_manager, 'update_callback'):
            self.paint_manager.t = self.t
            self.paint_manager.update_callback()
            self.updateGL()
        
    def start_timer(self):
        """Start the timer."""
        if self.timer:
            self.timer.start()
        
    def stop_timer(self):
        """Stop the timer."""
        if self.timer:
            self.timer.stop()
        
    def showEvent(self, e):
        """Called when the window is shown (for the first time or after
        minimization). It starts the timer."""
        # start simulation when showing window
        self.start_timer()
        
    def hideEvent(self, e):
        """Called when the window is hidden (e.g. minimized). It stops the
        timer."""
        # stop simulation when hiding window
        self.stop_timer()
    
    
# Basic widgets helper functions and classes
# ------------------------------------------
def create_custom_widget(bindings=None,
                         antialiasing=False,
                         constrain_ratio=False,
                         constrain_navigation=False,
                         display_fps=False,
                         update_interval=None,
                         autosave=None,
                         getfocus=True,
                        **companion_classes):
    """Helper function to create a custom widget class from various parameters.
    
    Arguments:
      * bindings=None: the bindings class, instance, or a list of those.
      * antialiasing=False: whether to activate antialiasing or not. It can
        hurt performance.
      * constrain_ratio=False: if True, the ratio is 1:1 at all times.
      * constrain_navigation=True: if True, the viewbox cannot be greater
        than [-1,1]^2 by default (but it can be customized in 
        interactionmanager.MAX_VIEWBOX).
      * display_fps=False: whether to display the FPS.
      * update_interval=None: if not None, a special widget with automatic
        timer update is created. This variable then refers to the time interval
        between two successive updates (in seconds).
      * **companion_classes: keyword arguments with the companion classes.
    
    """
    # use the GalryTimerWidget if update_interval is not None
    if update_interval is not None:
        baseclass = GalryTimerWidget
    else:
        baseclass = GalryWidget
    
    if bindings is None:
        bindings = []
    if type(bindings) != list and type(bindings) != tuple:
        bindings = [bindings]
    
    # create the custom widget class
    class MyWidget(baseclass):
        """Automatically-created Galry widget."""
        def __init__(self):
            # antialiasing
            format = QGLFormat()
            if antialiasing:
                format.setSampleBuffers(True)
            super(MyWidget, self).__init__(format=format, autosave=autosave,
                getfocus=getfocus)
        
        def initialize(self):
            self.set_bindings(*bindings)
            self.set_companion_classes(**companion_classes)
            self.constrain_ratio = constrain_ratio
            self.constrain_navigation = constrain_navigation
            self.display_fps = display_fps
            self.initialize_companion_classes()
            if update_interval is not None:
                self.initialize_timer(dt=update_interval)

    return MyWidget
    
class AutodestructibleWindow(QtGui.QMainWindow):
    """Special QT window that can be destroyed automatically after a given
    timeout. Useful for automatic debugging or benchmarking."""
    autodestruct = None
    
    def __init__(self, **kwargs):
        super(AutodestructibleWindow, self).__init__()
        # This is important in interaction sessions: it allows the widget
        # to clean everything up as soon as we close the window (otherwise
        # it is just hidden).
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.initialize(**kwargs)
        
    def set_autodestruct(self, autodestruct=None):
        # by default, use global variable
        if autodestruct is None:
            # use the autodestruct option in command line by default
            autodestruct = "autodestruct" in sys.argv
            if autodestruct is False:
                global AUTODESTRUCT
                autodestruct = AUTODESTRUCT
        # option for autodestructing the window after a fixed number of 
        # seconds: useful for automatic testing
        if autodestruct is True:
            # 3 seconds by default, if True
            global DEFAULT_AUTODESTRUCT
            autodestruct = DEFAULT_AUTODESTRUCT
        if autodestruct:
            log_info("window autodestruction in %d second(s)" % (autodestruct / 1000.))
        self.autodestruct = autodestruct
        
    def initialize(self, **kwargs):
        pass
        
    def kill(self):
        if self.autodestruct:
            self.timer.stop()
            self.close()
        
    def showEvent(self, e):
        if self.autodestruct:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(self.autodestruct)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.kill)
            self.timer.start()
            
def create_basic_window(widget=None, size=None, position=(100, 100),
                        autodestruct=None):
    """Create a basic QT window with a Galry widget inside.
    
    Arguments:
      * widget: a class or instance deriving from GalryWidget.
      * size=None: the size of the window as a tuple (width, height).
      * position=(100, 100): the initial position of the window on the screen,
        in pixels (x, y).
      * autodestruct=None: if not None, it is the time, in seconds, before the
        window closes itself.
    
    """
    class BasicWindow(AutodestructibleWindow):
        """Automatically-created QT window."""
        def initialize(self, widget=widget, size=size, position=position,
                       autodestruct=autodestruct):
            """Create a basic window to display a single widget.
            
            Arguments:
              * widget: a class or instance deriving from GalryWidget.
              * size=None: the size of the window as a tuple (width, height).
              * position=(100, 100): the initial position of the window on the screen,
                in pixels (x, y).
              * autodestruct=None: if not None, it is the time, in seconds, before the
                window closes itself.
              
            """
            self.set_autodestruct(autodestruct)
            # default widget
            if widget is None:
                widget = GalryWidget()
            # if widget is not an instance of GalryWidget, maybe it's a class,
            # then try to instanciate it
            if not isinstance(widget, GalryWidget):
                widget = widget()
            widget.window = self
            # create widget
            self.widget = widget
            if size is None:
                size = self.widget.width, self.widget.height
            # show widget
            self.setGeometry(*(position + size))
            self.setCentralWidget(self.widget)
            self.show()
            
        def closeEvent(self, e):
            """Clean up memory upon closing."""
            self.widget.paint_manager.cleanup()
            
    return BasicWindow
    
def show_basic_window(widget_class=None, window_class=None, size=None,
            position=(100, 100), autodestruct=None, **kwargs):
    """Create a custom widget and/or window and show it immediately.
    
    Arguments:
      * widget_class=None: the class deriving from GalryWidget.
      * window_class=None: the window class, deriving from `QMainWindow`.
      * size=None: the size of the window as a tuple (width, height).
      * position=(100, 100): the initial position of the window on the screen,
        in pixels (x, y).
      * autodestruct=None: if not None, it is the time, in seconds, before the
        window closes itself.
      * **kwargs: keyword arguments with the companion classes and other 
        parameters that are passed to `create_custom_widget`.
    
    """
    # default widget class
    if widget_class is None:
        widget_class = create_custom_widget(**kwargs)
    # defaut window class
    if window_class is None:
        window_class = create_basic_window(widget_class, size=size,
            position=position, autodestruct=autodestruct)
    # create and show window
    return show_window(window_class)
    