import bpy
import math
import os
from mathutils import Vector
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

def render_cube(config, output_subfolder="cube"):
    """render the cube from multiple angles"""
    # ensure output directory exists
    output_dir = os.path.join(config["output"]["directory"], output_subfolder)
    os.makedirs(output_dir, exist_ok=True)
    
    # setup scene
    setup_scene(config)
    
    # create cube
    cube = create_cube(config)
    
    # setup environment
    setup_environment(config)
    
    # set up camera
    bpy.ops.object.camera_add()
    camera = bpy.context.active_object
    camera.location = (5, 0, 0)
    camera.rotation_euler = (math.pi/2, 0, math.pi/2)

    # make camera active
    bpy.context.scene.camera = camera

    # create a target for the camera to point at
    target = Vector(tuple(config["cube"]["location"]))

    # render multiple views around the cube
    num_images = config["camera"]["num_images"]
    distance = config["camera"]["distance"]
    vertical_movement = config["camera"]["vertical_movement"]

    print(f"rendering {num_images} cube images to {output_dir}")
    
    for i in range(num_images):
        # calculate camera position on a circle
        angle = (2.0 * math.pi * i) / num_images
        x = distance * math.cos(angle)
        y = distance * math.sin(angle)
        z = vertical_movement * math.sin(angle/2)
        
        camera.location = (x, y, z)
        
        # point camera at the cube
        direction = target - camera.location
        rot_quat = direction.to_track_quat('-Z', 'Y')
        camera.rotation_euler = rot_quat.to_euler()
        
        # render and save the image
        bpy.context.scene.render.filepath = f"{output_dir}/cube_{i:03d}.png"
        bpy.ops.render.render(write_still=True)
    
    print(f"finished rendering {num_images} cube images")

if __name__ == "__main__":
    # when run directly, load config and render
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "configs", "cube.yaml")
    config = load_config(config_path)
    render_cube(config)