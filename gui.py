import tkinter as tk
from tkinter import messagebox
from debugger import Debugger

class DebuggerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ReLive Debugger")
        self.root.geometry("600x400")

        # Initialize Debugger
        self.debugger = Debugger(self)

        # UI Components
        self.code_input_label = tk.Label(root, text="Enter Python Script Path:")
        self.code_input_label.pack(pady=5)

        self.script_path_entry = tk.Entry(root, width=50)
        self.script_path_entry.pack(pady=5)

        self.start_button = tk.Button(root, text="Start Debugging", command=self.start_debugging)
        self.start_button.pack(pady=20)

        # Add Debugger Control Buttons
        self.step_button = tk.Button(root, text="Step Over", command=self.step_over)
        self.step_button.pack(pady=5)

        self.continue_button = tk.Button(root, text="Continue", command=self.continue_debugging)
        self.continue_button.pack(pady=5)

        self.quit_button = tk.Button(root, text="Quit", command=self.quit_debugger)
        self.quit_button.pack(pady=5)

        self.console_output = tk.Text(root, height=10, width=70)
        self.console_output.pack(pady=10)

    def start_debugging(self):
        script_path = self.script_path_entry.get()
        if not script_path:
            messagebox.showerror("Error", "Please provide a valid script path")
            return

        self.console_output.delete(1.0, tk.END)
        
        self.debugger.start_debugging(script_path)
        self.console_output.insert(tk.END, f"Debugging {script_path}...\n")

    def update_console(self, text):
        """Update the console with new output."""
        self.console_output.insert(tk.END, text)
        self.console_output.yview(tk.END)

    def step_over(self):
        """Step over the current line of code."""
        self.debugger.step_over()

    def continue_debugging(self):
        """Continue debugging until the next breakpoint."""
        self.debugger.continue_debugging()

    def quit_debugger(self):
        """Quit the debugger and close the window."""
        self.root.quit()
