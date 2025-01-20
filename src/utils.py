from io import StringIO
import queue
import time


class OutputBuffer:
    def __init__(self):
        self.queue = queue.Queue()
        self.buffer = StringIO()

    def write(self, text):
        self.buffer.write(text)
        self.queue.put(text)

    def flush(self):
        pass

    def getvalue(self):
        return self.buffer.getvalue()
    def clear(self):
        self.buffer = StringIO()
 
 
class ProgramState:
    def __init__(self):
        self.variables = {}
        self.stack_frames = []
        self.current_line = None
        self.output = ""
        self.timestamp = time.time()
