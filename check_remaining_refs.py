#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查是否还有 input_handler 的剩余引用
"""
import os

def check_remaining_references():
    """检查项目中是否还有 input_handler 的引用"""
    print("Checking for remaining input_handler references...")
    
    # 检查 game.py
    with open('program/game.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'input_handler' in content:
        print('Found remaining input_handler references in game.py:')
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'input_handler' in line and not line.strip().startswith('#'):  # 忽略注释行
                print(f'  Line {i}: {line.strip()}')
    else:
        print('✓ No input_handler references found in game.py')
    
    # 检查 UI 目录下的其他文件
    print("\nChecking UI files...")
    for root, dirs, files in os.walk('program/ui'):
        for file in files:
            if file.endswith('.py') and file != 'input_handler.py':
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'input_handler' in content:
                    print(f'Found input_handler reference in {filepath}:')
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'input_handler' in line and not line.strip().startswith('#'):
                            print(f'  Line {i}: {line.strip()}')
    
    print('\n✓ Completed check for input_handler references')

if __name__ == "__main__":
    check_remaining_references()