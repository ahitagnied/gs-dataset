import os
import sys

# + the current directory to python's path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from scripts.distorted_cube import load_config, render_cube

def main():
    # get the absolute path to the config file
    config_path = os.path.join(current_dir, "configs", "distorted_cube.yaml")
    
    # print status for debugging
    print(f"looking for config at: {config_path}")
    if os.path.exists(config_path):
        print("config file found!")
    else:
        print("config file NOT found!")
    
    # load the config
    config = load_config(config_path)
    
    # render the cube directly to train and test folders
    render_cube(config, train_ratio=0.33)

if __name__ == "__main__":
    main()