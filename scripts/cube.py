import bpy
import math
import os
import json
from mathutils import Vector, Matrix
import yaml

def load_config(config_path):
    """load configuration from yaml file"""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def setup_scene(config):
    """setup the basic blender scene"""
    # clear existing scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj)
    
    # set render settings
    bpy.context.scene.render.engine = 'CYCLES'
    resolution = config["output"]["resolution"]
    bpy.context.scene.render.resolution_x = resolution[0]
    bpy.context.scene.render.resolution_y = resolution[1]
    bpy.context.scene.render.image_settings.file_format = config["output"]["format"]
    bpy.context.scene.cycles.samples = config["output"]["samples"]
    bpy.context.scene.render.film_transparent = True # <-- make background transparent like NeRO

def create_cube(config):
    """create a shiny cube based on config"""
    # create a cube
    size = config["cube"]["size"]
    location = config["cube"]["location"]
    bpy.ops.mesh.primitive_cube_add(size=size, location=tuple(location))
    cube = bpy.context.active_object

    # create a shiny material for the cube
    material = bpy.data.materials.new("ShinyMaterial")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links

    # clear default nodes
    for node in nodes:
        nodes.remove(node)

    # add principled bsdf node
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs['Metallic'].default_value = config["cube"]["material"]["metallic"]
    bsdf.inputs['Roughness'].default_value = config["cube"]["material"]["roughness"]
    
    if 'Specular' in bsdf.inputs:
        bsdf.inputs['Specular'].default_value = config["cube"]["material"]["specular"]
    elif 'Specular IOR' in bsdf.inputs:  # Blender 4.0 name
        bsdf.inputs['Specular IOR'].default_value = config["cube"]["material"]["specular"]
    else:
        print("warning: couldn't find specular input, using default value")

    bsdf.location = (0, 0)

    # add output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)

    # link nodes
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

    # assign material to cube
    if cube.data.materials:
        cube.data.materials[0] = material
    else:
        cube.data.materials.append(material)
    
    return cube

def setup_environment(config):
    """set up the hdri environment"""
    # add hdri environment map
    if bpy.context.scene.world is None:
        # Create a new world if it doesn't exist
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    else:
        world = bpy.context.scene.world
        
    world.use_nodes = True
    world_nodes = world.node_tree.nodes
    world_links = world.node_tree.links

    # clear default nodes
    for node in world_nodes:
        world_nodes.remove(node)

    # add environment texture node
    env_tex = world_nodes.new(type='ShaderNodeTexEnvironment')
    env_tex.image = bpy.data.images.load(config["environment"]["hdri_path"])
    env_tex.location = (-300, 0)

    # add background node
    background = world_nodes.new(type='ShaderNodeBackground')
    background.location = (0, 0)

    # add output node
    world_output = world_nodes.new(type='ShaderNodeOutputWorld')
    world_output.location = (300, 0)

    # link nodes
    world_links.new(env_tex.outputs['Color'], background.inputs['Color'])
    world_links.new(background.outputs['Background'], world_output.inputs['Surface'])

def render_cube(config, train_ratio):
    """render objects and save to train and test folders based on script name"""
    # get script name for folder name
    import inspect
    folder_name = os.path.splitext(os.path.basename(inspect.getfile(inspect.currentframe())))[0]
    
    # setup directories
    output_dir = config["output"]["directory"]
    object_dir = os.path.join(output_dir, folder_name)
    train_dir = os.path.join(object_dir, "train")
    test_dir = os.path.join(object_dir, "test")
    
    os.makedirs(object_dir, exist_ok=True)
    os.makedirs(train_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    
    # setup scene and camera
    setup_scene(config)
    cube = create_cube(config)
    setup_environment(config)
    
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.location = (5, 0, 0)
    camera.rotation_euler = (math.pi/2, 0, math.pi/2)
    bpy.context.scene.camera = camera
    
    # calculate camera parameters
    camera_data = camera.data
    aspect_ratio = config["output"]["resolution"][0] / config["output"]["resolution"][1]
    camera_angle_x = 2 * math.atan(math.tan(camera_data.angle / 2) * aspect_ratio)
    target = Vector(tuple(config["cube"]["location"]))

    # render settings
    num_images = config["camera"]["num_images"]
    distance = config["camera"]["distance"]
    vertical_movement = config["camera"]["vertical_movement"]
    num_train = math.floor(num_images * train_ratio)
    
    print(f"rendering {num_train} train images and {num_images - num_train} test images")
    
    train_camera_params = []
    test_camera_params = []
    
    for i in range(num_images):
        # set camera position
        angle = (2.0 * math.pi * i) / num_images
        rotation_step = 0.031415926535897934
        
        x = distance * math.cos(angle)
        y = distance * math.sin(angle)
        z = vertical_movement * math.sin(angle/2)
        
        camera.location = (x, y, z)
        
        # aim camera at target
        direction = target - camera.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_quat.to_euler()
        
        # get transform matrix
        camera_to_world = camera.matrix_world.copy()
        transform_matrix = [list(row) for row in camera_to_world]
            
        # save to train or test
        is_train = i < num_train
        
        if is_train:
            current_dir = train_dir
            img_index = i
            file_path = f"./train/r_{i}"
            train_camera_params.append({
                "file_path": file_path,
                "rotation": rotation_step,
                "transform_matrix": transform_matrix,
                "camera_angle_x": camera_angle_x
            })
        else:
            current_dir = test_dir
            img_index = i - num_train
            file_path = f"./test/r_{img_index}"
            test_camera_params.append({
                "file_path": file_path,
                "rotation": rotation_step,
                "transform_matrix": transform_matrix,
                "camera_angle_x": camera_angle_x
            })

        # render image
        bpy.context.scene.render.filepath = os.path.join(current_dir, f"r_{img_index}.png")
        bpy.ops.render.render(write_still=True)
    
    # create transform json files
    create_transform_json(config, train_camera_params, "transforms_train.json", folder_name)
    create_transform_json(config, test_camera_params, "transforms_test.json", folder_name)
    
    print(f"finished rendering {num_images} images")

def create_transform_json(config, camera_params, output_filename, folder_name):
    """create transform.json file in nero dataset format"""
    if not camera_params:
        print(f"warning: no camera parameters for {output_filename}")
        return
        
    # setup output directory
    output_dir = config["output"]["directory"]
    object_dir = os.path.join(output_dir, folder_name)
    
    # create transform data
    transform_data = {
        "camera_angle_x": camera_params[0]["camera_angle_x"],
        "frames": []
    }
    
    # add frames data
    for params in camera_params:
        frame_data = {
            "file_path": params["file_path"],
            "rotation": params["rotation"],
            "transform_matrix": params["transform_matrix"]
        }
        transform_data["frames"].append(frame_data)
    
    # save json file
    transform_json_path = os.path.join(object_dir, output_filename)
    with open(transform_json_path, "w") as f:
        json.dump(transform_data, f, indent=4)
    
    print(f"saved {output_filename} to {transform_json_path}")

if __name__ == "__main__":
    # when run directly, load config and render
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "cube.yaml")
    config = load_config(config_path)
    render_cube(config)