from flask import Flask, request, jsonify, send_from_directory, current_app
import bdb
import threading
import os
import sys
from io import StringIO
import queue
import inspect
import time
from werkzeug.serving import run_simple
from flask.ctx import RequestContext

app = Flask(__name__, static_folder='frontend')
debugger_instance = None

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

class WebDebugger(bdb.Bdb):
    def __init__(self):
        super().__init__()
        self.breakpoints = {}
        self.stack_frames = []
        self.variables = {}
        self.exception = None
        self.output_buffer = OutputBuffer()
        self.current_frame = None
        self.step_over_depth = None
        self.is_running = False
        self._lock = threading.Lock()
        self.stored_stdout = None
        self.stored_stderr = None
        self.next_command = None
        self.current_line = None

    def user_line(self, frame):
        with self._lock:
            self.current_frame = frame
            self.current_line = frame.f_lineno
            self.stack_frames = self._get_stack_frames()
            self.variables = self._get_variables(frame)
            
            while self.is_running and not self.next_command:
                time.sleep(0.1)
            
            if self.next_command:
                command = self.next_command
                self.next_command = None
                
                if command == 'step':
                    self.set_step()
                elif command == 'step_over':
                    self.set_next(frame)
                elif command == 'continue':
                    self.set_continue()
                elif command == 'quit':
                    self.set_quit()

    def user_return(self, frame, return_value):
        with self._lock:
            if self.step_over_depth and len(self._get_stack_frames()) < self.step_over_depth:
                self.step_over_depth = None

    def user_exception(self, frame, exc_info):
        exc_type, exc_value, exc_traceback = exc_info
        self.exception = f"{exc_type.__name__}: {str(exc_value)}"

    def _get_stack_frames(self):
        stack = []
        frame = self.current_frame
        while frame:
            stack.append({
                'file': frame.f_code.co_filename,
                'line': frame.f_lineno,
                'function': frame.f_code.co_name,
                'locals': {k: repr(v) for k, v in frame.f_locals.items()},
                'source': self._get_source_context(frame)
            })
            frame = frame.f_back
        return stack

    def _get_source_context(self, frame, context_lines=3):
        try:
            lines, start = inspect.getsourcelines(frame.f_code)
            current_line = frame.f_lineno - start
            start_line = max(0, current_line - context_lines)
            end_line = min(len(lines), current_line + context_lines + 1)
            return {
                'lines': lines[start_line:end_line],
                'start_line': start + start_line,
                'current_line': frame.f_lineno
            }
        except:
            return None

    def _get_variables(self, frame):
        return {
            'locals': {k: repr(v) for k, v in frame.f_locals.items()},
            'globals': {k: repr(v) for k, v in frame.f_globals.items() 
                       if not k.startswith('__')}
        }

    def setup_io(self):
        self.stored_stdout = sys.stdout
        self.stored_stderr = sys.stderr
        sys.stdout = self.output_buffer
        sys.stderr = self.output_buffer

    def restore_io(self):
        if self.stored_stdout and self.stored_stderr:
            sys.stdout = self.stored_stdout
            sys.stderr = self.stored_stderr

def run_code(code, debugger):
    try:
        debugger.setup_io()
        debugger.is_running = True
        compiled_code = compile(code, '<string>', 'exec')
        debugger.run(compiled_code)
    except Exception as e:
        debugger.set_exception(str(e))
        print(f"Exception occurred: {str(e)}")
    finally:
        debugger.restore_io()
        debugger.is_running = False

@app.route("/")
def index():
    return send_from_directory(current_app.static_folder, 'index.html')

@app.route("/start", methods=["POST"])
def start_debugger():
    global debugger_instance
    code = request.json.get("code")
    if not code:
        return jsonify({"error": "No code provided"}), 400

    if debugger_instance and debugger_instance.is_running:
        debugger_instance.set_quit()
        time.sleep(0.5)

    debugger_instance = WebDebugger()
    threading.Thread(target=run_code, args=(code, debugger_instance), daemon=True).start()
    return jsonify({"message": "Debugger started"})

@app.route("/status", methods=["GET"])
def get_status():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    status = {
        "is_running": debugger_instance.is_running,
        "stack_frames": debugger_instance.stack_frames,
        "variables": debugger_instance.variables,
        "breakpoints": debugger_instance.breakpoints.get('<string>', {}),
        "exception": debugger_instance.exception,
        "output": debugger_instance.output_buffer.getvalue(),
        "current_line": debugger_instance.current_line
    }
    return jsonify(status)

@app.route("/breakpoints", methods=["POST"])
def set_breakpoints():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    breakpoints = request.json.get("breakpoints", [])
    debugger_instance.clear_all_breaks()
    
    for bp in breakpoints:
        line = int(bp)
        debugger_instance.set_break('<string>', line)
    
    return jsonify({
        "message": "Breakpoints set",
        "breakpoints": list(debugger_instance.breakpoints.get('<string>', {}).keys())
    })

@app.route("/control", methods=["POST"])
def control_execution():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
    
    action = request.json.get("action")
    
    if action in ['step', 'step_over', 'continue', 'quit']:
        debugger_instance.next_command = action
    else:
        return jsonify({"error": "Invalid action"}), 400
    
    return jsonify({"message": f"Action '{action}' performed"})

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)