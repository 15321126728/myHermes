#!/usr/bin/env python3
"""
Blind Maze Explorer - Systematically explores unknown mazes using DFS.
Usage: python3 explorer.py [maze_id]
"""
import subprocess
import sys
import os
from collections import deque

MAZE_GAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maze_game.sh")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Direction: (name, delta_row, delta_col)
DIRECTIONS = [('N', -1, 0), ('S', 1, 0), ('E', 0, 1), ('W', 0, -1)]
OPPOSITES = {'N': 'S', 'S': 'N', 'E': 'W', 'W': 'E'}

class MazeExplorer:
    def __init__(self, maze_id):
        self.maze_id = maze_id
        # Position tracking - start at relative (0, 0)
        self.row, self.col = 0, 0
        # Map storage: (r,c) -> char ('S', 'E', ' ', '#', or '?' for unknown)
        self.map_data = {}
        self.map_data[(0, 0)] = 'S'
        # Visited open cells (not walls)
        self.visited = set([(0, 0)])
        # Boundary tracking
        self.min_r = self.max_r = 0
        self.min_c = self.max_c = 0
        
        # Start the maze game process
        self.proc = subprocess.Popen(
            [MAZE_GAME, str(maze_id)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        # Read welcome messages (4 lines)
        for _ in range(4):
            self.proc.stdout.readline()
    
    def _send(self, cmd):
        """Send a command and get the response."""
        self.proc.stdin.write(cmd + "\n")
        self.proc.stdin.flush()
        resp = self.proc.stdout.readline().strip()
        # Strip prompt prefix if present
        if resp.startswith("> "):
            resp = resp[2:]
        return resp
    
    def move(self, direction):
        """Move one step in direction. Returns (success, is_exit) tuple."""
        dr, dc = 0, 0
        for d_name, d_dr, d_dc in DIRECTIONS:
            if d_name == direction:
                dr, dc = d_dr, d_dc
                break
        
        resp = self._send(f"move {direction}")
        
        if resp == "hit wall":
            wall_pos = (self.row + dr, self.col + dc)
            self.map_data[wall_pos] = '#'
            self._update_bounds(wall_pos)
            return (False, False)
        elif resp == "reached exit":
            self.row += dr
            self.col += dc
            self.map_data[(self.row, self.col)] = 'E'
            self.visited.add((self.row, self.col))
            self._update_bounds((self.row, self.col))
            return (True, True)
        elif resp == "moved":
            self.row += dr
            self.col += dc
            pos = (self.row, self.col)
            if pos not in self.map_data:
                self.map_data[pos] = ' '
            self.visited.add(pos)
            self._update_bounds(pos)
            return (True, False)
        else:
            # Unexpected - try to handle gracefully
            return (False, False)
    
    def _update_bounds(self, pos):
        r, c = pos
        self.min_r = min(self.min_r, r)
        self.max_r = max(self.max_r, r)
        self.min_c = min(self.min_c, c)
        self.max_c = max(self.max_c, c)
    
    def can_move_to(self, direction):
        """Check if we can move in a direction without actually doing it."""
        dr, dc = 0, 0
        for d_name, d_dr, d_dc in DIRECTIONS:
            if d_name == direction:
                dr, dc = d_dr, d_dc
                break
        next_pos = (self.row + dr, self.col + dc)
        return self.map_data.get(next_pos) != '#'
    
    def send_batch(self, commands):
        """Send a batch movement command. commands is a list of direction strings.
        Returns list of (success, is_exit) tuples."""
        if not commands:
            return []
        
        cmd = "move " + " & ".join(commands)
        resp = self._send(cmd)
        results = [r.strip() for r in resp.split("&")]
        
        batch_results = []
        for i, direction in enumerate(commands):
            dr, dc = 0, 0
            for d_name, d_dr, d_dc in DIRECTIONS:
                if d_name == direction:
                    dr, dc = d_dr, d_dc
                    break
            
            r_text = results[i] if i < len(results) else ""
            
            if r_text == "hit wall":
                wall_pos = (self.row + dr, self.col + dc)
                self.map_data[wall_pos] = '#'
                self._update_bounds(wall_pos)
                batch_results.append((False, False))
            elif r_text == "reached exit":
                self.row += dr
                self.col += dc
                self.map_data[(self.row, self.col)] = 'E'
                self.visited.add((self.row, self.col))
                self._update_bounds((self.row, self.col))
                batch_results.append((True, True))
            elif r_text == "moved":
                self.row += dr
                self.col += dc
                pos = (self.row, self.col)
                if pos not in self.map_data:
                    self.map_data[pos] = ' '
                self.visited.add(pos)
                self._update_bounds(pos)
                batch_results.append((True, False))
            else:
                batch_results.append((False, False))
        
        return batch_results
    
    def get_unexplored_directions(self):
        """Return list of directions from current position that aren't known walls and haven't been visited."""
        result = []
        for direction, dr, dc in DIRECTIONS:
            next_pos = (self.row + dr, self.col + dc)
            # Skip known walls
            if self.map_data.get(next_pos) == '#':
                continue
            # If we haven't visited the next cell, it's unexplored
            if next_pos not in self.visited:
                result.append(direction)
        return result
    
    def bfs_path_to(self, target_pos):
        """BFS through visited cells to find shortest path from current position to target.
        Returns list of direction names."""
        if (self.row, self.col) == target_pos:
            return []
        
        # BFS through visited/open cells
        visited = set()
        queue = deque()
        queue.append(((self.row, self.col), []))
        visited.add((self.row, self.col))
        
        while queue:
            pos, path = queue.popleft()
            for direction, dr, dc in DIRECTIONS:
                next_pos = (pos[0] + dr, pos[1] + dc)
                
                # Can only traverse open cells (visited or known not-a-wall)
                cell = self.map_data.get(next_pos)
                if cell == '#':
                    continue  # wall
                if next_pos not in self.visited:
                    continue  # unexplored
                
                if next_pos == target_pos:
                    return path + [direction]
                
                if next_pos not in visited:
                    visited.add(next_pos)
                    queue.append((next_pos, path + [direction]))
        
        return None  # no path found
    
    def explore(self):
        """Explore the maze using DFS."""
        # Stack of (row, col) representing DFS path
        stack = [(self.row, self.col)]
        
        while stack:
            current = (self.row, self.col)
            
            # Find unexplored directions from current position
            unexplored = self.get_unexplored_directions()
            
            if unexplored:
                direction = unexplored[0]
                success, is_exit = self.move(direction)
                if success:
                    stack.append((self.row, self.col))
            else:
                # Pop current position - all directions explored
                stack.pop()
                if stack:
                    target = stack[-1]  # previous position in DFS stack
                    path = self.bfs_path_to(target)
                    if path:
                        # Use batch commands for efficiency
                        self.send_batch(path)
    
    def fill_unknown(self):
        """Fill all unknown cells with walls."""
        # For each visited cell, check adjacent cells
        for r, c in list(self.visited):
            for _, dr, dc in DIRECTIONS:
                adj = (r + dr, c + dc)
                if adj not in self.map_data:
                    self.map_data[adj] = '#'
        
        # Also extend bounds to include all known cells
        all_cells = list(self.map_data.keys())
        for r, c in all_cells:
            self._update_bounds((r, c))
        
        # Fill any gaps within bounds
        for r in range(self.min_r, self.max_r + 1):
            for c in range(self.min_c, self.max_c + 1):
                if (r, c) not in self.map_data:
                    self.map_data[(r, c)] = '#'
    
    def get_map_string(self):
        """Generate the final maze map as a string."""
        self.fill_unknown()
        
        rows = []
        for r in range(self.min_r, self.max_r + 1):
            row_chars = []
            for c in range(self.min_c, self.max_c + 1):
                cell = self.map_data.get((r, c), '#')
                row_chars.append('#' if cell == '?' else cell)
            rows.append(''.join(row_chars))
        
        return '\n'.join(rows)
    
    def save_map(self):
        """Save the maze map to output file."""
        # Exit the game
        self._send("exit")
        self.proc.terminate()
        
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        output_path = os.path.join(OUTPUT_DIR, f"{self.maze_id}.txt")
        
        map_str = self.get_map_string()
        with open(output_path, "w") as f:
            f.write(map_str)
        
        print(f"Maze {self.maze_id} map saved to {output_path}")
        print(f"Map dimensions: rows={self.max_r - self.min_r + 1}, cols={self.max_c - self.min_c + 1}")
        print(f"Visited {len(self.visited)} cells")
        print(f"Map:\n{map_str}\n")

def main():
    if len(sys.argv) > 1:
        maze_ids = [int(sys.argv[1])]
    else:
        maze_ids = list(range(1, 11))
    
    for maze_id in maze_ids:
        print(f"\n{'='*60}")
        print(f"Exploring maze {maze_id}...")
        print(f"{'='*60}")
        
        explorer = MazeExplorer(maze_id)
        explorer.explore()
        explorer.save_map()

if __name__ == "__main__":
    main()
