import os
import imageio

def make_gif(
    folder: str = 'output/cube/train',
    out: str = 'train.gif',
    duration: float = 0.1
):
    """load images from folder (alphabetical) and save as a looping gif."""
    files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))
    )
    images = [
        imageio.imread(os.path.join(folder, f))[:, :, :3]
        for f in files
    ]
    imageio.mimsave(out, images, duration=duration)
    print(f'saved gif to {out} ({len(images)} frames @ {duration}s/frame)')

if __name__ == '__main__':
    make_gif()
