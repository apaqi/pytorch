"""
The weak_script annotation needs to be here instead of inside torch/jit/ so it
can be used in other places in torch/ (namely torch.nn) without running into
circular dependency problems
"""

import weakref
import inspect
try:
    import builtins  # py3
except Exception:
    import __builtin__ as builtins  # py2

compiled_weak_fns = weakref.WeakKeyDictionary()
COMPILATION_PENDING = object()
COMPILED = object()


def createResolutionCallback(frames_up=0):
    """
    Creates a function which, given a string variable name,
    returns the value of the variable in the scope of the caller of
    the function which called createResolutionCallback (by default).

    This is used to enable access in-scope Python variables inside
    TorchScript fragments.

    frames_up is number of additional frames to go up on the stack.
    The default value is 0, which correspond to the frame of the caller
    of createResolutionCallback. Also for example, if frames_up is set
    to 1, then the frame of the caller's caller of createResolutionCallback
    will be taken.

    For example, the following program prints 2::

        def bar():
            cb = createResolutionCallback(1)
            print(cb("foo"))

        def baz():
            foo = 2
            bar()

        baz()
    """
    frame = inspect.stack()[1 + frames_up][0]
    f_locals = frame.f_locals
    f_globals = frame.f_globals

    def env(key):
        if key in f_locals:
            return f_locals[key]
        elif key in f_globals:
            return f_globals[key]
        elif hasattr(builtins, key):
            return getattr(builtins, key)
        else:
            return None

    return env


def weak_script(fn, _frames_up=0):
    """
    Marks a function as a weak script function. When used in a script function
    or ScriptModule, the weak script function will be lazily compiled and
    inlined in the graph. When not used in a script function, the weak script
    annotation has no effect.
    """
    compiled_weak_fns[fn] = {
        "status": COMPILATION_PENDING,
        "compiled_fn": None,
        "rcb": createResolutionCallback(_frames_up + 1)
    }
    return fn
