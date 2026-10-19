WALNUT BEDROOM — DETAIL EDITION / V3
Blender 5.2.2 LTS | Cycles | Native render 7680 x 5416 pixels

OPEN THE PROJECT
Open bedroom.blend in Blender. All six source PBR images are packed inside.
Materials, editable meshes/curves, lighting, camera and metric dimensions remain
editable. No add-on, external texture path or cloth-cache download is required.
The duvet is deterministic sculpted geometry, not a live cloth simulation.

WHAT CHANGED
- Photographed walnut diffuse, tangent normal and satin roughness maps.
- Leather diffuse/patina, pore normal map, variable roughness and piping.
- Cross-woven cotton/linen shader relief and subtle yarn variation.
- Plumper asymmetric duvet, shorter side drape, corner creases and hem stitches.
- Bolster corduroy ribs, pillow seams and double saddle stitches on the ottoman.
- Uneven masonry geometry plus two scales of bump; warm sconce light pools.
- Reference-calibrated camera retained. f/11 keeps bed/materials sharp.

RENDER
The PNG master is rendered directly by Cycles at 7680 x 5416, not upscaled.
32 maximum adaptive samples, minimum 8, threshold 0.065, OpenImageDenoise using
albedo + normal guides. CPU rendering was used on this workstation.
For a future offline production pass, increase samples to 128-512 and reduce
the threshold; this increases render time. Do not mistake sample count for pixels.
The commercial visual is a design study, not a real photographed bedroom.

REBUILD FROM THE SCRIPT
Download build_bedroom.py and bedroom-pbr-textures.zip from the website.
Extract the ZIP beside the script; the resulting layout must be:
  build_bedroom.py
  textures/natural_walnut_veneer_Diffuse.jpg
  textures/natural_walnut_veneer_nor_gl.jpg
  textures/natural_walnut_veneer_Rough.jpg
  textures/brown_leather_Diffuse.jpg
  textures/brown_leather_nor_gl.jpg
  textures/brown_leather_Rough.jpg

Run (adjust Blender's executable path):
  blender --background --python build_bedroom.py -- --stage preview
  blender --background --python build_bedroom.py -- --stage final
The first command builds/saves the scene and renders a small proof. The second
loads the saved .blend and renders native 8K. --stage all performs both.

WEB VERSION
The GLB is a lightweight cutaway with compressed geometry and embedded baked PBR
maps. Textile, leather, wood and masonry detail is retained within a browser
budget. Wool microfibers and final ray-traced illumination remain in Blender.
The GLB mirror uses environment reflections, not dynamic planar reflections of
the room; use the Cycles render/.blend for optically traced mirror/glass detail.
Four material images on the website are crops of the actual 8K master.
For hosting compatibility, the web download reassembles verified byte parts into
the original lossless PNG. This is not a tiled render or an upscale. A direct
8K JPEG is also available. The original PNG remains in the local output folder.

TEXTURE CREDITS / CC0
Natural Walnut Veneer — Jenelle van Heerden
https://polyhaven.com/a/natural_walnut_veneer
Brown Leather — Rob Tuytel
https://polyhaven.com/a/brown_leather
License: https://polyhaven.com/license
Source maps: 2K JPG Diffuse / OpenGL normal / Roughness, checksum-verified.
The original reference image supplied by the user is not a texture/model mesh.
