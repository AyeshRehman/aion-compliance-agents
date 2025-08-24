# show_structure.py
import os

def show_tree(path, prefix="", max_depth=3, current_depth=0):
    """Display directory tree structure"""
    if current_depth >= max_depth:
        return
    
    items = []
    try:
        items = sorted(os.listdir(path))
    except PermissionError:
        return
    
    # Filter out common ignored directories
    ignore = {'.git', '__pycache__', '.vscode', 'node_modules', '.env'}
    items = [item for item in items if item not in ignore]
    
    for i, item in enumerate(items):
        item_path = os.path.join(path, item)
        is_last = i == len(items) - 1
        
        # Print current item
        current_prefix = "└── " if is_last else "├── "
        print(f"{prefix}{current_prefix}{item}")
        
        # Recursively show subdirectories
        if os.path.isdir(item_path):
            next_prefix = prefix + ("    " if is_last else "│   ")
            show_tree(item_path, next_prefix, max_depth, current_depth + 1)

# Show your compliance project structure
print("PROJECT STRUCTURE:")
print("=" * 50)
show_tree("src/copilots/compliance")