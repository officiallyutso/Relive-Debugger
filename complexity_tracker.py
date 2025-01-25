import ast
import sympy
from typing import Dict, List, Tuple

class ComplexityAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.complexities = {}
        self.current_function = None
        
    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.complexities[node.name] = {
            'time': 'O(1)',  # Default complexity
            'space': 'O(1)',
            'loops': [],
            'recursion': False
        }
        self.generic_visit(node)
        
    def visit_For(self, node):
        if self.current_function:
            # Analyze loop bounds
            loop_info = self._analyze_loop_bounds(node)
            self.complexities[self.current_function]['loops'].append(loop_info)
            self._update_complexity(loop_info)
        self.generic_visit(node)
        
    def visit_While(self, node):
        if self.current_function:
            loop_info = self._analyze_while_condition(node)
            self.complexities[self.current_function]['loops'].append(loop_info)
            self._update_complexity(loop_info)
        self.generic_visit(node)
        
    def _analyze_loop_bounds(self, node) -> dict:
        try:
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name):
                if node.iter.func.id == 'range':
                    args = node.iter.args
                    if len(args) == 1:
                        return {'type': 'linear', 'bound': 'n'}
                    elif len(args) == 2:
                        return {'type': 'linear', 'bound': 'n'}
                    elif len(args) == 3:
                        return {'type': 'linear', 'bound': 'n'}
            return {'type': 'unknown', 'bound': 'n'}
        except:
            return {'type': 'unknown', 'bound': 'n'}
            
    def _analyze_while_condition(self, node) -> dict:
        # Basic while loop analysis
        return {'type': 'unknown', 'bound': 'n'}
        
    def _update_complexity(self, loop_info):
        current = self.complexities[self.current_function]
        if loop_info['type'] == 'linear':
            if current['time'] == 'O(1)':
                current['time'] = 'O(n)'
            elif current['time'] == 'O(n)':
                current['time'] = 'O(n²)'
            current['space'] = 'O(n)'

# Add to your WebDebugger class
class CoverageTracker:
    def __init__(self):
        self.covered_lines = set()
        self.branch_coverage = {}
        self.function_coverage = set()
        
    def mark_line(self, filename: str, line: int):
        self.covered_lines.add((filename, line))
        
    def mark_branch(self, filename: str, line: int, branch_taken: bool):
        if (filename, line) not in self.branch_coverage:
            self.branch_coverage[(filename, line)] = set()
        self.branch_coverage[(filename, line)].add(branch_taken)
        
    def mark_function(self, function_name: str):
        self.function_coverage.add(function_name)
        
    def get_coverage_stats(self):
        return {
            'line_coverage': len(self.covered_lines),
            'branch_coverage': len(self.branch_coverage),
            'function_coverage': len(self.function_coverage)
        }

# Add to your WebDebugger class
class AnimationController:
    def __init__(self):
        self.animation_queue = []
        self.animation_speed = 1.0
        self.is_animating = False
        
    def add_step(self, line_number: int, variables: Dict, stack: List):
        self.animation_queue.append({
            'line': line_number,
            'variables': variables,
            'stack': stack,
            'timestamp': time.time()
        })
        
    def clear(self):
        self.animation_queue = []
        self.is_animating = False
        
    def set_speed(self, speed: float):
        self.animation_speed = max(0.1, min(5.0, speed))
        
    def get_next_frame(self):
        if not self.animation_queue:
            return None
        return self.animation_queue.pop(0)