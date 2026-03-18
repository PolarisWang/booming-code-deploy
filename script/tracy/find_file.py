"""
用法：python find_file.py <filename> [search_root]

在 search_root（默认当前目录）下递归查找与 filename 同名的文件。
每行输出一个匹配的完整路径，无匹配时输出为空。
"""
import os
import sys

SKIP_DIRS = {'.git', '.claude', 'node_modules', '__pycache__', '.vs', 'Build', 'build'}

def find(filename, root):
    matches = []
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for f in files:
            if f == filename:
                matches.append(os.path.join(dirpath, f))
    return matches

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('usage: find_file.py <filename> [search_root]', file=sys.stderr)
        sys.exit(1)
    filename = os.path.basename(sys.argv[1])
    root = sys.argv[2] if len(sys.argv) > 2 else '.'
    results = find(filename, root)
    print('\n'.join(results))
