import bdb  # Changed from 'from bdb import Bdb' to 'import bdb'
import inspect
import sys
import time
import threading
import copy
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter
from .utils import OutputBuffer, ProgramState
from .profiler import PerformanceProfiler
from .tracker import ExecutionTracker
from .evaluator import CodeEvaluator

class WebDebugger(bdb.Bdb):  # Changed from Bdb to bdb.Bdb
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
        self.selected_code = None
        self.selected_range = None
        self.execution_tracker = ExecutionTracker()
        self.profiler = PerformanceProfiler()
        self.conditional_breakpoints = {}
        self.evaluator = CodeEvaluator(self)
        
    def break_here(self, frame):
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno

        # First check if there's a breakpoint at this line
        if not super().break_here(frame):
            return False

        # If there's a condition, evaluate it
        if filename in self.conditional_breakpoints and lineno in self.conditional_breakpoints[filename]:
            condition = self.conditional_breakpoints[filename][lineno]
            try:
                # Evaluate condition in the current frame's context
                result = eval(condition, frame.f_globals, frame.f_locals)
                return bool(result)
            except Exception as e:
                print(f"Error evaluating breakpoint condition: {e}")
                return True  # Break anyway if condition evaluation fails
        
        return True
    
    def get_break_info(self, filename, lineno):
        """Get information about a specific breakpoint."""
        if self.get_break(filename, lineno):
            condition = None
            if (filename in self.conditional_breakpoints and 
                lineno in self.conditional_breakpoints[filename]):
                condition = self.conditional_breakpoints[filename][lineno]
            return {
                'line': lineno,
                'condition': condition
            }
        return None
    
    def set_conditional_break(self, filename, lineno, condition=None):
        """Set a breakpoint with an optional condition."""
        self.set_break(filename, lineno)
        
        if condition:
            if filename not in self.conditional_breakpoints:
                self.conditional_breakpoints[filename] = {}
            self.conditional_breakpoints[filename][lineno] = condition
        elif filename in self.conditional_breakpoints:
            # Remove condition if setting a regular breakpoint
            self.conditional_breakpoints[filename].pop(lineno, None)

    def clear_conditional_break(self, filename, lineno):
        """Clear a conditional breakpoint."""
        self.clear_break(filename, lineno)
        if filename in self.conditional_breakpoints:
            self.conditional_breakpoints[filename].pop(lineno, None)
            
    def clear_break(self, filename, lineno):
        """Clear both the breakpoint and any associated condition."""
        super().clear_break(filename, lineno)
        if filename in self.conditional_breakpoints:
            self.conditional_breakpoints[filename].pop(lineno, None)

    def get_all_breakpoints(self):
        """Get all breakpoints including their conditions."""
        result = {}
        for filename, lines in self.breakpoints.items():
            result[filename] = {}
            for lineno in lines:
                condition = None
                if (filename in self.conditional_breakpoints and 
                    lineno in self.conditional_breakpoints[filename]):
                    condition = self.conditional_breakpoints[filename][lineno]
                result[filename][lineno] = {'condition': condition}
        return result

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
                caller_name = '<module>'
                if frame.f_back:
                    caller_name = frame.f_back.f_code.co_name
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