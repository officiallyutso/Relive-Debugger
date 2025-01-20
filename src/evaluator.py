import ast

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