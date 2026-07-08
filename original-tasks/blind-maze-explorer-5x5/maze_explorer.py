#!/usr/bin/env python3
"""Blind Maze Explorer - DFS exploration and mapping."""
import subprocess, sys, time, os
from collections import deque

class MazeExplorer:
    def __init__(self, server_script):
        self.maze = {(0,0): 'S'}
        self.pos = (0,0)
        self.min_r = self.max_r = 0
        self.min_c = self.max_c = 0
        self.visited = {(0,0)}
        self.dirs = [('N',-1,0),('S',1,0),('E',0,1),('W',0,-1)]

        self.proc = subprocess.Popen(['python3', server_script],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, bufsize=1)
        time.sleep(0.2)
        for _ in range(4):
            self.proc.stdout.readline()

    def _cmd(self, txt):
        self.proc.stdin.write(f"{txt}\n"); self.proc.stdin.flush()
        r = self.proc.stdout.readline().strip()
        if r.startswith('> '): r = r[2:]
        return r.strip()

    def move(self, d): return self._cmd(f"move {d}")

    def explore(self):
        stack = [(self.pos, 0)]
        while stack:
            pos, _ = stack[-1]
            unexplored = []
            for d,dr,dc in self.dirs:
                np = (pos[0]+dr, pos[1]+dc)
                if self.maze.get(np,'?') != '#' and np not in self.visited:
                    unexplored.append(d)
            if not unexplored:
                stack.pop()
                if stack:
                    target = stack[-1][0]
                    path = self._bfs(target)
                    if path:
                        for d in path:
                            dr,dc = self._vec(d)
                            r = self.move(d)
                            if r in ('moved','reached exit'):
                                self.pos = (self.pos[0]+dr, self.pos[1]+dc)
                                self._bound(self.pos)
                continue
            d = unexplored[0]; dr,dc = self._vec(d)
            r = self.move(d)
            if r == 'moved':
                self.pos = (self.pos[0]+dr, self.pos[1]+dc)
                if self.maze.get(self.pos,'?') == '?': self.maze[self.pos] = ' '
                self.visited.add(self.pos); self._bound(self.pos)
                stack.append((self.pos, 0))
            elif r == 'reached exit':
                self.pos = (self.pos[0]+dr, self.pos[1]+dc)
                self.maze[self.pos] = 'E'; self.visited.add(self.pos)
                self._bound(self.pos); stack.append((self.pos, 0))
                print(f"  EXIT at {self.pos}", flush=True)
            else:
                wp = (self.pos[0]+dr, self.pos[1]+dc)
                self.maze[wp] = '#'; self._bound(wp)
        print(f"Visited {len(self.visited)} cells. Bounds: r[{self.min_r},{self.max_r}] c[{self.min_c},{self.max_c}]", flush=True)

    def _vec(self,d):
        for dd,dr,dc in self.dirs:
            if dd==d: return dr,dc
        return 0,0

    def _bfs(self, target):
        if self.pos == target: return []
        q = deque([(self.pos, [])]); seen = {self.pos}
        while q:
            p, path = q.popleft()
            for d,dr,dc in self.dirs:
                np = (p[0]+dr, p[1]+dc)
                if np == target and np in self.visited and self.maze.get(np,'?') != '#':
                    return path + [d]
                if np not in seen and np in self.visited and self.maze.get(np,'?') not in ('#','?'):
                    seen.add(np); q.append((np, path+[d]))
        return None

    def _bound(self, p):
        r,c=p; self.min_r=min(self.min_r,r); self.max_r=max(self.max_r,r)
        self.min_c=min(self.min_c,c); self.max_c=max(self.max_c,c)

    def build_map(self, filepath):
        """Fill in unknown cells (all must be walls since all spaces are reachable)."""
        # Step 1: corner rule - if N and W are walls, NW diagonal is wall (repeat till stable)
        changed = True
        while changed:
            changed = False
            for r in range(self.min_r, self.max_r+1):
                for c in range(self.min_c, self.max_c+1):
                    if self.maze.get((r,c),'?') != '?': continue
                    n = self.maze.get((r-1,c),'?')
                    s = self.maze.get((r+1,c),'?')
                    w = self.maze.get((r,c-1),'?')
                    e = self.maze.get((r,c+1),'?')
                    if (n=='#' and w=='#') or (n=='#' and e=='#') or (s=='#' and w=='#') or (s=='#' and e=='#'):
                        self.maze[(r,c)] = '#'; changed = True

        # Step 2: any '?' adjacent (NSEW) to a visited path cell -> '#'
        for p in list(self.visited):
            r,c = p
            for d,dr,dc in self.dirs:
                a = (r+dr, c+dc)
                if self.maze.get(a,'?') == '?': self.maze[a] = '#'

        # Step 3: propagate - any '?' adjacent to a non-'?' cell -> '#'
        changed = True
        while changed:
            changed = False
            for r in range(self.min_r, self.max_r+1):
                for c in range(self.min_c, self.max_c+1):
                    if self.maze.get((r,c),'?') != '?': continue
                    for d,dr,dc in self.dirs:
                        a = (r+dr, c+dc)
                        if self.maze.get(a,'?') != '?':
                            self.maze[(r,c)] = '#'; changed = True; break

        # Step 4: remaining '?' -> '#'
        for r in range(self.min_r, self.max_r+1):
            for c in range(self.min_c, self.max_c+1):
                if self.maze.get((r,c),'?') == '?': self.maze[(r,c)] = '#'

        rows = self.max_r - self.min_r + 1
        cols = self.max_c - self.min_c + 1
        grid = []
        for r in range(self.min_r, self.max_r+1):
            row = []
            for c in range(self.min_c, self.max_c+1):
                row.append(self.maze.get((r,c), '#'))
            grid.append(row)

        with open(filepath, 'w') as f:
            for row in grid:
                f.write(''.join(row) + '\n')

        print(f"\nSaved to {filepath}", flush=True)
        for row in grid:
            print(''.join(row))

    def close(self):
        try: self._cmd("exit")
        except: pass
        try: self.proc.terminate(); self.proc.wait(timeout=2)
        except: self.proc.kill()

def main():
    e = MazeExplorer("/opt/data/blind-maze-explorer-5x5/protected/maze_server.py")
    try:
        e.explore()
        e.build_map("/opt/data/blind-maze-explorer-5x5/maze_map.txt")
    finally:
        e.close()

if __name__ == "__main__":
    main()
