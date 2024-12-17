import pdb
import sys
import threading
import io
import os
import queue

class Debugger:
    def __init__(self, gui):
        self._gui = gui
        self._pdb = None
        self._thread = None
        self._command_queue = queue.Queue() 
        self._event = threading.Event() 

    def start_debugging(self, script_path):
        """Start debugging in a separate thread to avoid blocking the UI."""
        if isinstance(script_path, str):
            script_path = os.path.abspath(script_path)

        print(f"Using script path: {script_path}")

        if not os.path.exists(script_path):
            self._gui.update_console(f"Error: File does not exist at path: {script_path}\n")
            return

        if not os.access(script_path, os.R_OK):
            self._gui.update_console(f"Error: File is not readable at path: {script_path}\n")
            return

        # Start debugging in a new thread
        self._thread = threading.Thread(target=self._run_debugger, args=(script_path,))
        self._thread.start()

    def _run_debugger(self, script_path):
        """Runs the script with pdb and sets it up for debugging."""
        try:
            current_dir = os.getcwd()
            print(f"Current working directory: {current_dir}")
            print(f"Attempting to open script file: {script_path}")

            try:
                with open(script_path, 'r') as script_file:
                    print("File successfully opened.")
                    script_code = script_file.read()
                    sys.stdout = io.StringIO()
                    sys.stderr = io.StringIO()

                    self._pdb = pdb.Pdb()
                    self._pdb.set_trace() 

                    self._execute_script(script_code)

                    output = sys.stdout.getvalue()
                    error_output = sys.stderr.getvalue()

                    if output:
                        self._gui.update_console(output)
                    if error_output:
                        self._gui.update_console(error_output)

            except Exception as e:
                self._gui.update_console(f"Error: {str(e)}\n")

        except Exception as e:
            self._gui.update_console(f"Error occurred: {str(e)}\n")

    def _execute_script(self, script_code):
        """Executes the script code, listens for user commands in a loop."""
        self._pdb.runcall(self._run_code, script_code)

    def _run_code(self, code):
        """Runs the code in the debugger, listens for commands like 'continue' or 'step'."""
        while True:
            if not self._command_queue.empty():
                command = self._command_queue.get()

                if command == 'continue':
                    self._pdb.set_continue()
                elif command == 'step':
                    self._pdb.set_step() 

            # Allow the debugger to step through the code
            try:
                self._pdb.run(code)
                self._event.wait()
            except Exception as e:
                self._gui.update_console(f"Error during execution: {str(e)}\n")
                break

    def step_over(self):
        """Step over the current line of code."""
        if self._pdb:
            self._command_queue.put('step')
            self._event.set()

    def continue_debugging(self):
        """Continue debugging until the next breakpoint."""
        if self._pdb:
            self._command_queue.put('continue')
            self._event.set()
