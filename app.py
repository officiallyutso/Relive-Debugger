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
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
import json
import copy
import ast

app = Flask(__name__, static_folder='frontend')
debugger_instance = None

class ProgramState:
    def __init__(self):
        self.variables = {}
        self.stack_frames = []
        self.current_line = None
        self.output = ""
        self.timestamp = time.time()

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
        
        
        
class ExecutionTracker:
    def __init__(self):
        self.execution_path = []
        self.call_graph = {}
        self.current_calls = []
        
    def add_execution_step(self, line_no, code, event_type):
        """Track a single execution step"""
        # Clean and escape the code for Mermaid compatibility
        clean_code = code.strip().replace('"', '\'').replace('\n', ' ')
        if len(clean_code) > 30:
            clean_code = clean_code[:27] + '...'
            
        self.execution_path.append({
            'line': line_no,
            'code': clean_code,
            'event': event_type,
            'timestamp': time.time(),
            'call_depth': len(self.current_calls)
        })

    def add_function_call(self, caller_name, callee_name):
        """Track a function call relationship"""
        # Initialize caller in call graph if not exists
        if caller_name not in self.call_graph:
            self.call_graph[caller_name] = {
                'calls': set(),
                'called_from': set()
            }
            
        # Initialize callee in call graph if not exists
        if callee_name not in self.call_graph:
            self.call_graph[callee_name] = {
                'calls': set(),
                'called_from': set()
            }
            
        # Record the call relationship
        self.call_graph[caller_name]['calls'].add(callee_name)
        self.call_graph[callee_name]['called_from'].add(caller_name)
        self.current_calls.append(callee_name)

    def remove_function_call(self, callee_name):
        """Remove the most recent call to the function"""
        if self.current_calls and self.current_calls[-1] == callee_name:
            self.current_calls.pop()
    
    def get_execution_flowchart(self):
        """Generate Mermaid flowchart from execution path"""
        if not self.execution_path:
            return "flowchart TB\nstart[No execution steps yet]"
            
        nodes = []
        edges = []
        node_ids = {}
        last_node = None
        
        for i, step in enumerate(self.execution_path):
            node_id = f"node{i}"
            # Add tooltips using Mermaid click events
            label = f"{step['line']}: {step['code']}"
            nodes.append(f"{node_id}[\"{label}\"]")
            nodes.append(f"click {node_id} callback \"Line {step['line']}<br/>Code: {step['code']}<br/>Event: {step['event']}\"")
            
            if last_node:
                edges.append(f"{last_node} --> {node_id}")
            last_node = node_id
            
        return "flowchart TB\n" + "\n".join(nodes) + "\n" + "\n".join(edges)
        
    def get_call_graph(self):
        """Generate Mermaid diagram for call graph"""
        if not self.call_graph:
            return "flowchart LR\nstart[No function calls yet]"
            
        nodes = []
        edges = []
        
        # Convert sets to lists for consistent ordering
        for func in sorted(self.call_graph.keys()):
            # Clean function name for Mermaid compatibility
            clean_func = func.replace('<', '').replace('>', '').replace(' ', '_')
            
            # Add tooltips for function nodes
            nodes.append(f"{clean_func}[\"{func}\"]")
            calls = len(self.call_graph[func]['calls'])
            called_by = len(self.call_graph[func]['called_from'])
            nodes.append(f"click {clean_func} callback \"Function: {func}<br/>Calls: {calls}<br/>Called by: {called_by}\"")
            
            # Add edges for each function call
            for called in sorted(self.call_graph[func]['calls']):
                clean_called = called.replace('<', '').replace('>', '').replace(' ', '_')
                edges.append(f"{clean_func} --> {clean_called}")
                
        return "flowchart LR\n" + "\n".join(nodes) + "\n" + "\n".join(edges)

class PerformanceProfiler:
    def __init__(self):
        self.function_times = {}
        self.current_functions = {}
        self._start_times = {}
        
    def start_function(self, func_name, line_no):
        """Start timing a function"""
        timestamp = time.time()
        self._start_times[func_name] = timestamp
        
        if func_name not in self.function_times:
            self.function_times[func_name] = {
                'total_time': 0,
                'calls': 0,
                'avg_time': 0,
                'last_call_time': 0,
                'line': line_no
            }
            
        self.function_times[func_name]['calls'] += 1
        
    def end_function(self, func_name):
        """End timing a function"""
        if func_name in self._start_times:
            end_time = time.time()
            elapsed = end_time - self._start_times[func_name]
            
            self.function_times[func_name]['total_time'] += elapsed
            self.function_times[func_name]['last_call_time'] = elapsed
            self.function_times[func_name]['avg_time'] = (
                self.function_times[func_name]['total_time'] / 
                self.function_times[func_name]['calls']
            )
            
            del self._start_times[func_name]
            
    def get_profile_data(self):
        """Get all profiling data"""
        return {
            'function_times': self.function_times,
            'total_execution_time': sum(
                data['total_time'] for data in self.function_times.values()
            )
        }

class CodeEvaluator:
    def __init__(self, debugger):
        self.debugger = debugger
        
    def dedent_code(self, code):
        """Remove common leading indentation from code."""
        lines = code.splitlines()
        content_lines = [line for line in lines if line.strip()]
        if not content_lines:
            return code
            
        min_indent = min(len(line) - len(line.lstrip()) for line in content_lines)
        
        dedented_lines = []
        for line in lines:
            if line.strip():  
                dedented_lines.append(line[min_indent:])
            else:
                dedented_lines.append('')
                
        return '\n'.join(dedented_lines)
        
    def evaluate(self, code, line_number=None):
        try:
            dedented_code = self.dedent_code(code)
            if self.debugger.current_frame:
                local_vars = dict(self.debugger.current_frame.f_locals)
                global_vars = dict(self.debugger.current_frame.f_globals)
            else:
                local_vars = {}
                global_vars = {}
            
            self.debugger.output_buffer.clear()
            
            try:
                tree = ast.parse(dedented_code, mode='eval')
                result = eval(dedented_code, global_vars, local_vars)
                return {
                    'result': repr(result),
                    'output': self.debugger.output_buffer.getvalue(),
                    'type': 'expression',
                    'side_effects': self.detect_side_effects(local_vars, global_vars)
                }
            except SyntaxError:
                tree = ast.parse(dedented_code, mode='exec')
                exec(dedented_code, global_vars, local_vars)
                return {
                    'result': None,
                    'output': self.debugger.output_buffer.getvalue(),
                    'type': 'statement',
                    'side_effects': self.detect_side_effects(local_vars, global_vars)
                }
                
        except Exception as e:
            return {
                'error': str(e),
                'output': self.debugger.output_buffer.getvalue(),
                'type': 'error'
            }

    def detect_side_effects(self, new_locals, new_globals):
        side_effects = []
        
        if self.debugger.current_frame:
            old_locals = self.debugger.current_frame.f_locals
            old_globals = self.debugger.current_frame.f_globals
            
            for key in new_locals:
                if key in old_locals:
                    if new_locals[key] != old_locals[key]:
                        side_effects.append(f"Modified local variable: {key}")
                else:
                    side_effects.append(f"New local variable: {key}")
            
            for key in new_globals:
                if key in old_globals:
                    if new_globals[key] != old_globals[key]:
                        side_effects.append(f"Modified global variable: {key}")
                else:
                    side_effects.append(f"New global variable: {key}")
                    
        return side_effects


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
        self.program_states = []
        self.current_state_index = -1
        self.max_states = 100
        self.evaluator = CodeEvaluator(self)
        self.selected_code = None
        self.selected_range = None
        self.execution_tracker = ExecutionTracker()
        self.profiler = PerformanceProfiler()

    def user_line(self, frame):
        with self._lock:
            self.current_frame = frame
            self.current_line = frame.f_lineno
            self.stack_frames = self._get_stack_frames()
            self.variables = self._get_variables(frame)
            
            code = self._get_line_code(frame)
            self.execution_tracker.add_execution_step(
                frame.f_lineno, 
                code,
                'line'
            )
            
            if not self.selected_range or (
                self.current_line >= self.selected_range[0] and 
                self.current_line <= self.selected_range[1]
            ):
            
                self._save_state()
            
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
                elif command == 'step_back':
                    self._restore_previous_state()
                elif command == 'quit':
                    self.set_quit()
    def evaluate_code(self, code, line_number=None):
        return self.evaluator.evaluate(code, line_number)

    def user_return(self, frame, return_value):
        with self._lock:
            if frame.f_code.co_name != '<module>':
                self.profiler.end_function(frame.f_code.co_name)
                # Remove function from current calls stack
                self.execution_tracker.remove_function_call(frame.f_code.co_name)
            super().user_return(frame, return_value)
    def get_profile_data(self):
        """Get profiling data for visualization"""
        return self.profiler.get_profile_data()
            
    def user_call(self, frame, argument_list):
        with self._lock:
            if frame.f_code.co_name != '<module>':
                self.profiler.start_function(
                    frame.f_code.co_name,
                    frame.f_lineno
                )
                # Get caller name from previous frame if available
                caller_name = '<module>'
                if frame.f_back:
                    caller_name = frame.f_back.f_code.co_name
                # Add function call to execution tracker
                self.execution_tracker.add_function_call(
                    caller_name,
                    frame.f_code.co_name
                )
            super().user_call(frame, argument_list)
            
    def _get_line_code(self, frame):
        try:
            lines, start = inspect.getsourcelines(frame.f_code)
            return lines[frame.f_lineno - start]
        except:
            return ""
            
    def get_visualization_data(self):
        """Get visualization data for frontend"""
        return {
            'execution_flowchart': self.execution_tracker.get_execution_flowchart(),
            'call_graph': self.execution_tracker.get_call_graph()
        }

    def user_exception(self, frame, exc_info):
        exc_type, exc_value, exc_traceback = exc_info
        self.exception = f"{exc_type.__name__}: {str(exc_value)}"

    def _get_stack_frames(self):
        stack = []
        frame = self.current_frame
        while frame:
            source_context = self._get_source_context(frame)
            stack.append({
                'file': frame.f_code.co_filename,
                'line': frame.f_lineno,
                'function': frame.f_code.co_name,
                'locals': {k: repr(v) for k, v in frame.f_locals.items()},
                'globals': {k: repr(v) for k, v in frame.f_globals.items() 
                           if not k.startswith('__')},
                'source': source_context
            })
            frame = frame.f_back
        return stack

    def _get_source_context(self, frame, context_lines=3):
        try:
            lines, start = inspect.getsourcelines(frame.f_code)
            current_line = frame.f_lineno - start
            start_line = max(0, current_line - context_lines)
            end_line = min(len(lines), current_line + context_lines + 1)
            source_lines = lines[start_line:end_line]
            highlighted_source = highlight(''.join(source_lines), PythonLexer(), HtmlFormatter())
            return {
                'lines': highlighted_source,
                'start_line': start + start_line,
                'current_line': frame.f_lineno
            }
        except:
            return None

    def _save_state(self):
        state = ProgramState()
        state.variables = copy.deepcopy(self.variables)
        state.stack_frames = copy.deepcopy(self.stack_frames)
        state.current_line = self.current_line
        state.output = self.output_buffer.getvalue()
        
        self.program_states.append(state)
        self.current_state_index = len(self.program_states) - 1
        
        if len(self.program_states) > self.max_states:
            self.program_states.pop(0)
            self.current_state_index -= 1

    def _restore_previous_state(self):
        if self.current_state_index > 0:
            self.current_state_index -= 1
            state = self.program_states[self.current_state_index]
            self.variables = state.variables
            self.stack_frames = state.stack_frames
            self.current_line = state.current_line

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

def run_code(code, debugger, start_line=None, end_line=None):
    try:
        debugger.setup_io()
        debugger.is_running = True
        
        if start_line is not None and end_line is not None:
            debugger.selected_range = (start_line, end_line)
            # selected lines extract karne keliye
            code_lines = code.split('\n')
            selected_code = '\n'.join(code_lines[start_line-1:end_line])
            debugger.selected_code = selected_code
            compiled_code = compile(selected_code, '<string>', 'exec')
        else:
            debugger.selected_range = None
            debugger.selected_code = None
            compiled_code = compile(code, '<string>', 'exec')
            
        debugger.run(compiled_code)
    except Exception as e:
        debugger.exception = str(e)
        print(f"Exception occurred: {str(e)}")
    finally:
        debugger.restore_io()
        debugger.is_running = False

@app.route("/")
def index():
    return send_from_directory(current_app.static_folder, 'index.html')

@app.route("/visualizations", methods=["GET"])
def get_visualizations():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
        
    try:
        data = debugger_instance.get_visualization_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/profile", methods=["GET"])
def get_profile_data():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
        
    try:
        data = debugger_instance.get_profile_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/evaluate", methods=["POST"])
def evaluate_code():
    global debugger_instance
    if not debugger_instance:
        return jsonify({"error": "Debugger not running"}), 400
        
    code = request.json.get("code")
    line_number = request.json.get("line_number")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
        
    result = debugger_instance.evaluate_code(code, line_number)
    return jsonify(result)

@app.route("/start", methods=["POST"])
def start_debugger():
    global debugger_instance
    code = request.json.get("code")
    start_line = request.json.get("start_line")
    end_line = request.json.get("end_line")
    
    if not code:
        return jsonify({"error": "No code provided"}), 400

    highlighted_code = highlight(code, PythonLexer(), HtmlFormatter())
    
    if debugger_instance and debugger_instance.is_running:
        debugger_instance.set_quit()
        time.sleep(0.5)

    debugger_instance = WebDebugger()
    threading.Thread(
        target=run_code, 
        args=(code, debugger_instance, start_line, end_line), 
        daemon=True
    ).start()
    
    return jsonify({
        "message": "Debugger started",
        "highlighted_code": highlighted_code
    })

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
        "current_line": debugger_instance.current_line,
        "states": len(debugger_instance.program_states),
        "current_state": debugger_instance.current_state_index
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
    valid_actions = ['step', 'step_over', 'continue', 'step_back', 'quit']
    
    if action not in valid_actions:
        return jsonify({"error": "Invalid action"}), 400
    
    debugger_instance.next_command = action
    return jsonify({"message": f"Action '{action}' performed"})

if __name__ == "__main__":
    app.run(debug=True, threaded=True, port=5000)