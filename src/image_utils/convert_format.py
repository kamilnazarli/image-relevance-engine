from PIL import Image
from pathlib import Path

images_folder = Path(r"C:\Users\User\OneDrive\Desktop\image-relevance-engine\data\images")

for image_path in images_folder.iterdir():
    if image_path.suffix.lower() != ".avif":
        continue

    converted_name = image_path.name.replace(".avif", ".png")
    # output_path = images_folder / converted_name
    output_path = image_path.with_suffix(".png")

    with Image.open(image_path) as img:
        img.save(output_path)
        image_path.unlink()
