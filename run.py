import os
import sys

# + the current directory to python's path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from scripts.cube import load_config, render_cube

def main():
    # get the absolute path to the config file
    config_path = os.path.join(current_dir, "configs", "cube.yaml")
    
    # print status for debugging
    print(f"Looking for config at: {config_path}")
    if os.path.exists(config_path):
        print("Config file found!")
    else:
        print("Config file NOT found!")
    
    # load the config
    config = load_config(config_path)
    
    # render the cube
    render_cube(config, "cube")

if __name__ == "__main__":
    main()