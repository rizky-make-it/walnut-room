"""Build an editable, self-contained bedroom; run with Blender --background --python.

Default: build, save, preview, final. Use -- --stage preview to inspect first;
then -- --stage final to render the saved scene without rebuilding it.
"""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector, Matrix

ROOT = Path(__file__).resolve().parent
SEED = 28
random.seed(SEED)
START = time.time()
COLL = None
M = {}


def log(message):
    print(f"[BEDROOM {time.time()-START:.1f}s] {message}", flush=True)


def rgba(hexcode):
    v = [int(hexcode.lstrip('#')[i:i+2], 16)/255 for i in (0, 2, 4)]
    return tuple(c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in v) + (1,)


def material(name, color, roughness=.5, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba(color)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value = rgba(color)
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Metallic'].default_value = metallic
    return mat


def node(mat, kind, name=None):
    n = mat.node_tree.nodes.new(kind)
    if name:
        n.label = name
    return n


def link(mat, source, out, dest, inp):
    mat.node_tree.links.new(source.outputs[out], dest.inputs[inp])


def ramp(mat, colors):
    n = node(mat, 'ShaderNodeValToRGB')
    cr = n.color_ramp
    cr.elements.remove(cr.elements[1])
    for i, (pos, col) in enumerate(colors):
        el = cr.elements[0] if i == 0 else cr.elements.new(pos)
        el.position = pos
        el.color = rgba(col)
    return n


def wood(name, axis='X', oak=False):
    mat = material(name, '#765139' if not oak else '#C6AD85', .38)
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Coat Weight'].default_value = .12
    bs.inputs['Coat Roughness'].default_value = .4
    tc = node(mat, 'ShaderNodeTexCoord')
    scale = node(mat, 'ShaderNodeVectorMath', 'Lengthwise grain orientation')
    scale.operation = 'MULTIPLY'
    scale.inputs[1].default_value = {'X':(1.1, 36, 28), 'Y':(32, 1.1, 28), 'Z':(32, 28, 1.1)}[axis]
    link(mat, tc, 'Generated', scale, 0)
    noise = node(mat, 'ShaderNodeTexNoise', 'Long natural wood grain')
    noise.inputs['Scale'].default_value = 2.1
    noise.inputs['Detail'].default_value = 3
    noise.inputs['Roughness'].default_value = .65
    link(mat, scale, 'Vector', noise, 'Vector')
    cols = [(0,'#9C805D'),(.32,'#B49A73'),(.63,'#C9B18C'),(1,'#DBCAA8')] if oak else [(0,'#352218'),(.28,'#523724'),(.52,'#785236'),(.74,'#936B47'),(1,'#B38B5F')]
    cr = ramp(mat, cols)
    link(mat, noise, 'Fac', cr, 'Fac')
    link(mat, cr, 'Color', bs, 'Base Color')
    bump = node(mat, 'ShaderNodeBump')
    bump.inputs['Strength'].default_value = .16
    bump.inputs['Distance'].default_value = .0009
    link(mat, noise, 'Fac', bump, 'Height')
    link(mat, bump, 'Normal', bs, 'Normal')
    rough = node(mat, 'ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = .32
    rough.inputs['To Max'].default_value = .48
    link(mat, noise, 'Fac', rough, 'Value')
    link(mat, rough, 'Result', bs, 'Roughness')
    return mat


def fabric(name, color, coarse=False):
    mat = material(name, color, .84)
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Sheen Weight'].default_value = .28
    bs.inputs['Sheen Roughness'].default_value = .7
    tc = node(mat, 'ShaderNodeTexCoord')
    noise = node(mat, 'ShaderNodeTexNoise', 'Fine woven fiber')
    noise.inputs['Scale'].default_value = 190 if coarse else 420
    noise.inputs['Detail'].default_value = 2
    link(mat, tc, 'Object', noise, 'Vector')
    bump = node(mat, 'ShaderNodeBump')
    bump.inputs['Strength'].default_value = .28 if coarse else .19
    bump.inputs['Distance'].default_value = .0013 if coarse else .0006
    link(mat, noise, 'Fac', bump, 'Height')
    link(mat, bump, 'Normal', bs, 'Normal')
    return mat


def plaster(name, color, scale=90, distance=.008):
    mat = material(name, color, .88)
    bs = mat.node_tree.nodes.get('Principled BSDF')
    tc = node(mat, 'ShaderNodeTexCoord')
    noise = node(mat, 'ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 3
    link(mat, tc, 'Object', noise, 'Vector')
    b = node(mat, 'ShaderNodeBump')
    b.inputs['Strength'].default_value = .5
    b.inputs['Distance'].default_value = distance
    link(mat, noise, 'Fac', b, 'Height')
    link(mat, b, 'Normal', bs, 'Normal')
    return mat


def build_materials():
    for a in 'XYZ':
        M['walnut'+a] = wood('Walnut | grain '+a, a)
    M['oak'] = wood('Oak | long floorboard grain', 'Y', True)
    M['black'] = material('Blackened bronze | satin', '#29251F', .32, .65)
    M['brass'] = material('Aged brass', '#C29A52', .27, .8)
    M['white'] = fabric('Ivory cotton | duvet and pillows', '#F0EBDD')
    M['sheet'] = fabric('Natural white fitted sheet', '#E5DFD2')
    M['ochre'] = fabric('Ochre linen', '#B88B3B', True)
    M['throw'] = fabric('Mustard woven throw', '#AF8034', True)
    M['thread'] = material('Golden linen thread', '#C7A065', .88)
    M['welt'] = fabric('Ivory stitched edging', '#D8D0BD')
    M['leather'] = material('Cognac leather | fine natural grain', '#87502D', .48)
    bs = M['leather'].node_tree.nodes.get('Principled BSDF')
    noise = node(M['leather'], 'ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 165
    noise.inputs['Detail'].default_value = 3
    b = node(M['leather'], 'ShaderNodeBump')
    b.inputs['Distance'].default_value = .0008
    b.inputs['Strength'].default_value = .32
    link(M['leather'], noise, 'Fac', b, 'Height')
    link(M['leather'], b, 'Normal', bs, 'Normal')
    M['leatherthread'] = material('Leather saddle stitch', '#B48554', .8)
    M['mortar'] = plaster('Warm lime mortar', '#C6B89F', 65, .006)
    M['wall'] = plaster('Warm chalk plaster', '#DCD3C1', 100, .002)
    M['brick'] = [plaster('Handmade beige brick '+str(i+1), c, 72, .006) for i,c in enumerate(['#D1BFA0','#CEBB9E','#D5C5A9','#C9B697','#D9C9AF','#D0C0A6'])]
    M['green'] = material('Olive glazed ceramic', '#778052', .25)
    M['ceramic'] = plaster('Unglazed warm ceramic', '#BCAC91', 150, .0012)
    M['ceramicwhite'] = material('Milk ceramic', '#E5DCC8', .32)
    M['book1'] = material('Book cover sage', '#767960', .85)
    M['book2'] = material('Book cover oatmeal', '#C9BA9D', .8)
    M['book3'] = material('Book cover muted aubergine', '#7B6662', .8)
    M['paper'] = material('Warm paper edges', '#DFD4BD', .9)
    M['mirror'] = material('Silver mirror', '#F2F3F1', .018, 1)
    M['glass'] = material('Clear blown glass', '#FFFFFF', .07)
    bs = M['glass'].node_tree.nodes.get('Principled BSDF')
    bs.inputs['Transmission Weight'].default_value = 1
    bs.inputs['IOR'].default_value = 1.46
    M['bulb'] = material('Warm frosted glowing bulb', '#FFE9BF', .3)
    bs = M['bulb'].node_tree.nodes.get('Principled BSDF')
    bs.inputs['Emission Color'].default_value = rgba('#FFE4AD')
    bs.inputs['Emission Strength'].default_value = 3.5
    M['shadeinside'] = material('Sconce warm reflector', '#D9C59D', .45, .35)
    for name, col in [('artpaper','#D8D2C8'),('artgray','#8B8984'),('artdark','#555552'),('artlight','#C5C3BA')]:
        M[name] = material(name, col, .95)
    rug = fabric('Rug | ivory sculpted woven waves', '#D9D0BA', True)
    bs = rug.node_tree.nodes.get('Principled BSDF')
    tc = node(rug, 'ShaderNodeTexCoord')
    wave = node(rug, 'ShaderNodeTexWave', 'Subtle rippling woven ridges')
    wave.wave_type = 'RINGS'
    wave.rings_direction = 'Z'
    wave.inputs['Scale'].default_value = 3.5
    wave.inputs['Distortion'].default_value = 5
    wave.inputs['Detail Scale'].default_value = .55
    wave.inputs['Detail Roughness'].default_value = .65
    link(rug, tc, 'Object', wave, 'Vector')
    bump = node(rug, 'ShaderNodeBump')
    bump.inputs['Strength'].default_value = .24
    bump.inputs['Distance'].default_value = .0025
    link(rug, wave, 'Color', bump, 'Height')
    old = bs.inputs['Normal'].links[0].from_node
    link(rug, old, 'Normal', bump, 'Normal')
    link(rug, bump, 'Normal', bs, 'Normal')
    cr = ramp(rug, [(0,'#D0C6B0'),(.55,'#DAD1BD'),(1,'#E0D7C5')])
    link(rug, wave, 'Fac', cr, 'Fac')
    link(rug, cr, 'Color', bs, 'Base Color')
    M['rug'] = rug


def collection(name):
    global COLL
    COLL = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(COLL)
    return COLL


def move(obj):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    COLL.objects.link(obj)
    return obj


def assign(obj, mat):
    if mat:
        obj.data.materials.append(M[mat] if isinstance(mat, str) else mat)
    return obj


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def box(name, loc, dims, mat=None, bevel=.012, rot=None):
    # Direct mesh construction avoids a dependency-graph update per brick/plank.
    x,y,z=(d/2 for d in dims)
    vertices=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
              (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    obj = mesh(name,vertices,faces,mat)
    obj.location = loc
    if rot:
        obj.rotation_euler = rot
    if bevel:
        mod = obj.modifiers.new('Soft crafted edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
        smooth(obj)
        normal = obj.modifiers.new('Weighted surface normals', 'WEIGHTED_NORMAL')
        normal.keep_sharp = True
        normal.weight = 30
    else:
        for p in obj.data.polygons:
            p.use_smooth=False
    return obj


def mesh(name, vertices, faces, mat=None, sub=0):
    data = bpy.data.meshes.new(name+' mesh')
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    COLL.objects.link(obj)
    assign(obj, mat)
    smooth(obj)
    if sub:
        m = obj.modifiers.new('Soft surface subdivision', 'SUBSURF')
        m.levels = sub
        m.render_levels = sub
    return obj


def sphere(name, loc, scale, mat, segments=48, rings=24):
    vertices=[(0,0,-1)]
    for j in range(1,rings):
        phi=-math.pi/2+math.pi*j/rings
        for i in range(segments):
            a=2*math.pi*i/segments
            vertices.append((math.cos(phi)*math.cos(a),math.cos(phi)*math.sin(a),math.sin(phi)))
    top=len(vertices)
    vertices.append((0,0,1))
    faces=[]
    for i in range(segments):
        ni=(i+1)%segments
        faces.append((0,1+ni,1+i))
        for j in range(rings-2):
            a=1+j*segments+i
            b=1+j*segments+ni
            faces.append((a,b,b+segments,a+segments))
        a=1+(rings-2)*segments+i
        b=1+(rings-2)*segments+ni
        faces.append((a,b,top))
    obj = mesh(name,vertices,faces,mat)
    obj.location = loc
    obj.scale = scale
    return obj


def cylinder(name, loc, radius, depth, mat, bevel=.008, rotation=None, vertices=64):
    obj=lathe(name,(0,0,0),[(radius,-depth/2),(radius,depth/2)],mat,vertices)
    obj.location=loc
    if rotation:
        obj.rotation_euler = rotation
    if bevel:
        m = obj.modifiers.new('Rounded rim', 'BEVEL')
        m.width = bevel
        m.segments = 3
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    smooth(obj)
    return obj


def curve(name, points, radius, mat, cyclic=False):
    data = bpy.data.curves.new(name+' path', 'CURVE')
    data.dimensions = '3D'
    data.resolution_u = 1
    data.bevel_depth = radius
    data.bevel_resolution = 2
    poly = data.splines.new('POLY')
    poly.points.add(len(points)-1)
    for p, co in zip(poly.points, points):
        p.co = (*co, 1)
    poly.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, data)
    COLL.objects.link(obj)
    assign(obj, mat)
    return obj


def rod(name, start, end, radius, mat):
    delta = Vector(end)-Vector(start)
    obj = cylinder(name, (Vector(start)+Vector(end))/2, radius, delta.length, mat, .002, vertices=24)
    obj.rotation_euler = delta.to_track_quat('Z','Y').to_euler()
    return obj


def lathe(name, loc, profile, mat, segments=64, cap=True):
    verts=[]
    for radius, z in profile:
        for i in range(segments):
            a=2*math.pi*i/segments
            verts.append((loc[0]+radius*math.cos(a),loc[1]+radius*math.sin(a),loc[2]+z))
    faces=[]
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i
            b=j*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    if cap:
        faces.append(tuple(reversed(range(segments))))
        faces.append(tuple((len(profile)-1)*segments+i for i in range(segments)))
    return mesh(name,verts,faces,mat)


def light(name, kind, loc, energy, color, target=None, size=1):
    data=bpy.data.lights.new(name,kind)
    data.energy=energy
    data.color=color
    if kind == 'AREA':
        data.shape='DISK'
        data.size=size
    elif kind in {'POINT','SPOT'}:
        data.shadow_soft_size=size
    obj=bpy.data.objects.new(name,data)
    COLL.objects.link(obj)
    obj.location=loc
    if target:
        obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()
    return obj


def build_room():
    collection('01 | Architecture')
    box('Continuous floor foundation',(0,-.7,-.11),(7.8,7.6,.16),'mortar',0)
    # Individually separated floorboards, with staggered end joints.
    width=.185
    for column in range(41):
        x=-3.8+column*width
        y=-4.45-(column%3)*.47
        row=0
        while y < 2.05:
            length=1.55+random.uniform(-.22,.22)
            end=min(y+length,2.1)
            start=max(y,-4.45)
            if end>start:
                obj=box(f'Oak plank {column+1:02d}.{row:02d}',(x,(start+end)/2,-.011),(width-.0025,end-start-.003,.035),'oak',.0015)
                obj.color=(random.uniform(.85,1),.9,.8,1)
            y+=length
            row+=1
    # Back wall has a real opening, rather than a luminous picture of a window.
    back=1.98
    wx0,wx1=-1.91,-.80
    wz0,wz1=.18,3.07
    box('Mortar back wall | left',((-3.8+wx0)/2,back,1.75),(wx0+3.8,.16,3.5),'mortar',0)
    box('Mortar back wall | right',((wx1+3.25)/2,back,1.75),(3.25-wx1,.16,3.5),'mortar',0)
    box('Mortar above window',((wx0+wx1)/2,back,3.29),(wx1-wx0,.16,.42),'mortar',0)
    box('Mortar below window',((wx0+wx1)/2,back,.075),(wx1-wx0,.16,.15),'mortar',0)
    # Small bevels and per-brick depth variation give a dimensional brick wall.
    bh=.074
    for row in range(44):
        z=.035+row*(bh+.008)
        x=-3.95-(row%2)*.16
        col=0
        while x<3.3:
            bw=.31+random.uniform(-.016,.016)
            lo=max(x,-3.8)
            hi=min(x+bw,3.25)
            intervals=[(lo,hi)]
            if z+bh/2>wz0 and z-bh/2<wz1:
                intervals=[(lo,min(hi,wx0)),(max(lo,wx1),hi)]
            for a,b in intervals:
                if b-a>.025:
                    box(f'Beige brick {row:02d}.{col:02d}.{a:.2f}',((a+b)/2,1.879+random.uniform(-.004,.004),z),(b-a,.065,bh+random.uniform(-.005,.004)),random.choice(M['brick']),.009)
            x+=bw+.009
            col+=1
    box('Left plaster wall',(-3.83,-.9,1.75),(.16,5.9,3.5),'wall',0)
    box('Right plaster wall',(3.29,-.9,1.75),(.16,5.9,3.5),'wall',0)
    # A rear ceiling strip permits indirect illumination without enclosing the camera.
    box('Ceiling',(0,.65,3.55),(7.8,2.8,.12),'wall',0)
    box('Left baseboard',(-3.72,-.9,.075),(.035,5.7,.14),'wall',.003)
    box('Right baseboard',(3.18,-.9,.075),(.035,5.7,.14),'wall',.003)
    for a,b in [(-3.73,wx0),(wx1,3.18)]:
        box('Back baseboard',((a+b)/2,1.807,.075),(b-a,.035,.14),'wall',.003)
    # Deep painted reveal and slim real frame.
    for x in [wx0-.035,wx1+.035]:
        box('Window vertical white reveal',(x,1.93,1.625),(.09,.29,3.00),'wall',.006)
    for z in [wz0-.025,wz1+.025]:
        box('Window horizontal white reveal',((wx0+wx1)/2,1.93,z),(1.30,.30,.08),'wall',.005)
    box('Window sill',((wx0+wx1)/2,1.80,.16),(1.35,.43,.055),'ceramicwhite',.006)
    for x in [wx0+.04,wx1-.04]:
        box('Window slim sash',(x,2.055,1.625),(.038,.045,2.85),'ceramicwhite',.003)
    for z in [wz0+.045,wz1-.045]:
        box('Window sash rail',((wx0+wx1)/2,2.055,z),(1.04,.045,.035),'ceramicwhite',.003)
    # Exterior geometry and foliage remain editable; a pale sky provides the backdrop.
    collection('02 | Exterior light garden')
    M['leaf']=material('Distant olive foliage','#6F8051',.8)
    M['leaflight']=material('Distant sunlit foliage','#9B9C63',.8)
    M['bark']=material('Olive branch','#6B6349',.9)
    for i in range(6):
        x=-2.15+i*.27
        y=3.25+random.random()*.7
        z=.55+random.random()*.6
        end=(x+random.uniform(-.25,.25),y,2.9+random.random()*.35)
        rod('Exterior olive branch',(x,y,z),end,.012,'bark')
        for j in range(18):
            t=random.uniform(.15,1)
            cx=x+(end[0]-x)*t+random.uniform(-.22,.22)
            cy=y+random.uniform(-.20,.2)
            cz=z+(end[2]-z)*t
            leaf=sphere('Olive leaf',(cx,cy,cz),(.027,.012,.075),'leaflight' if j%3==0 else 'leaf',12,6)
            leaf.rotation_euler=(random.random()*1.5,random.random()*1.5,random.random()*6.28)
    # Reference window is softly overexposed; retain optional garden for editing.
    COLL.hide_render=True


def build_bed():
    collection('03 | Walnut queen bed frame')
    cx=.54
    for x in [cx-.85,cx+.85]:
        box('Bed side rail',(x,.33,.35),(.075,2.18,.18),'walnutY',.009)
    for y in [-.79,1.49]:
        box('Bed frame cross rail',(cx,y,.35),(1.78,.075,.15),'walnutX',.008)
    for j in range(13):
        box('Mattress support slat '+str(j+1),(cx,-.66+j*.164,.425),(1.66,.075,.035),'walnutX',.003)
    # Rectangular sleds echo the reference's open square legs.
    for name,y,height in [('Headboard',1.52,1.28),('Footboard',-.84,.57)]:
        for x in [cx-.9,cx+.9]:
            box(name+' square upright',(x,y,height/2+.03),(.075,.08,height),'walnutZ',.008)
        box(name+' top horizontal',(cx,y,height),(1.88,.08,.075),'walnutX',.008)
        box(name+' lower horizontal',(cx,y,.08),(1.88,.08,.075),'walnutX',.008)
        panelheight=.54 if name=='Headboard' else .25
        panelz=.90 if name=='Headboard' else .33
        box(name+' walnut infill',(cx,y+.008,panelz),(1.73,.055,panelheight),'walnutX',.006)
    collection('04 | Mattress and linen')
    box('Queen mattress | 160 x 200 cm',(cx,.34,.575),(1.60,2,.32),'sheet',.12)
    for z in [.455,.695]:
        pts=[]
        for i in range(128):
            a=2*math.pi*i/128
            x=.782*math.copysign(abs(math.cos(a))**.24,math.cos(a))
            y=.982*math.copysign(abs(math.sin(a))**.24,math.sin(a))
            pts.append((cx+x,.34+y,z))
        curve('Mattress stitched welt',pts,.002,'welt',True)
    # Duvet is a single draped surface with soft side overhangs and a curved foot.
    nx,ny=100,132
    verts=[]
    def duvet_pos(u,v):
        xlocal=1.035*u
        y=-.755+1.875*v
        y+=.012*math.sin(5*u+2*v)+.007*math.sin(12*u-7*v)
        dropx=max(0,(abs(xlocal)-.74)/.295)
        dropy=max(0,(-.57-y)/.185)
        crown=.085*(1-u*u)*(.65+.35*math.sin(v*math.pi))
        wrinkles=(.016*math.sin(14*u+4*v)+.009*math.sin(29*u-11*v)+.008*math.sin(51*u+8*v))*(.35+.65*abs(u)**.7)
        diagonal=.026*math.sin(19*v+4*math.sin(3*u))*(.3+.7*abs(u))
        # Rounded corners hang freely above the rug instead of adding both drops.
        dx,dy=.43*(dropx**1.55),.39*(dropy**1.6)
        z=.79+crown-max(dx,dy)-.12*min(dx,dy)+wrinkles+diagonal
        # Folded upper cuff has a little loft.
        z+=.035*math.exp(-((v-.90)/.055)**2)
        return (cx+xlocal,y,z)
    for j in range(ny+1):
        for i in range(nx+1):
            verts.append(duvet_pos(-1+2*i/nx,j/ny))
    faces=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i
            faces.append((a,a+1,a+nx+2,a+nx+1))
    duvet=mesh('Duvet | sculpted cotton drape',verts,faces,'white',1)
    solid=duvet.modifiers.new('Cotton loft and hem thickness','SOLIDIFY')
    solid.thickness=.018
    solid.offset=-.4
    for side in [-1,1]:
        curve('Duvet side seam',[duvet_pos(side,j/ny) for j in range(ny+1)],.002,'welt')
    curve('Duvet foot hem',[duvet_pos(-1+2*i/nx,0) for i in range(nx+1)],.0025,'welt')
    # Store the sampling surface for the separate woven throw.
    build_pillow('White pillow left',(cx-.40,1.08,.88),(.76,.43,.17),'white',-.05)
    build_pillow('White pillow right',(cx+.40,1.09,.89),(.76,.43,.17),'white',.045)
    build_pillow('Mustard pillow left',(cx-.40,1.16,1.065),(.78,.46,.27),'ochre',-.065)
    build_pillow('Mustard pillow right',(cx+.40,1.14,1.065),(.78,.46,.27),'ochre',.045)
    # Long ribbed bolster, axis X, with realistic softly convex end caps.
    profile=[(.001,-.69),(.075,-.69),(.105,-.676),(.112,-.64),(.112,.64),(.105,.676),(.075,.69),(.001,.69)]
    bol=lathe('Ochre cylindrical bolster',(0,0,0),profile,'ochre',96)
    bol.rotation_euler[1]=math.pi/2
    bol.location=(cx,.86,.94)
    for j in range(104):
        x=cx-.655+j*1.31/103
        pts=[(x,.86+.113*math.cos(a*2*math.pi/48),.94+.113*math.sin(a*2*math.pi/48)) for a in range(48)]
        curve('Bolster woven rib',pts,.00125,'thread',True)
    for side in [-1,1]:
        pts=[(cx+side*.682,.86+.097*math.cos(a*2*math.pi/64),.94+.097*math.sin(a*2*math.pi/64)) for a in range(64)]
        curve('Bolster end piping',pts,.002,'thread',True)
    # Asymmetric throw crosses the foot and drapes down the left edge.
    verts=[]
    tx,ty=92,38
    def throw_pos(u,v):
        xlocal=-1.07+1.60*u
        y=-.40+.43*v+.105*u+.03*math.sin(6*u+3*v)
        sx=xlocal/1.035
        dv=(y+.755)/1.875
        base=duvet_pos(max(-1,min(1,sx)),dv)
        z=base[2]+.027+.018*math.sin(27*u+5*v)+.012*math.sin(19*v+3*u)
        z+=.022*math.exp(-((v-.83)/.09)**2)
        if xlocal < -1.035:
            z-=.10
        return (cx+xlocal,y,z)
    for j in range(ty+1):
        for i in range(tx+1):
            verts.append(throw_pos(i/tx,j/ty))
    faces=[(j*(tx+1)+i,j*(tx+1)+i+1,(j+1)*(tx+1)+i+1,(j+1)*(tx+1)+i) for j in range(ty) for i in range(tx)]
    throw=mesh('Mustard throw | loosely draped',verts,faces,'throw',1)
    sol=throw.modifiers.new('Woven thickness','SOLIDIFY')
    sol.thickness=.006
    for edge in [0,1]:
        curve('Throw bound edge',[throw_pos(i/tx,edge) for i in range(tx+1)],.002,'thread')
    for j in range(64):
        v=j/63
        p=throw_pos(1,v)
        curve('Throw tassel', [p,(p[0]+.018,p[1]+.003,p[2]-.004),(p[0]+.048,p[1]+.004,p[2]-.025)],.0012,'thread')


def build_pillow(name,loc,dims,mat,angle):
    # Two inflated rectangular patches, sewn together at a slim perimeter.
    nx,ny=36,24
    verts=[]
    for side in [1,-1]:
        for j in range(ny+1):
            v=-1+2*j/ny
            for i in range(nx+1):
                u=-1+2*i/nx
                x=dims[0]/2*u*(1-.07*abs(v)**8)
                y=dims[1]/2*v*(1-.10*abs(u)**8)
                puff=max(0,(1-u*u)*(1-v*v))**.55
                wrinkle=.004*math.sin(27*u+8*v)*(abs(u)**6+abs(v)**6)*puff
                z=side*(.008+dims[2]/2*puff+wrinkle)+.025*v
                verts.append((x,y,z))
    row=nx+1
    layer=(nx+1)*(ny+1)
    faces=[]
    for k,side in enumerate([1,-1]):
        for j in range(ny):
            for i in range(nx):
                a=k*layer+j*row+i
                face=(a,a+1,a+row+1,a+row)
                faces.append(face if side==1 else tuple(reversed(face)))
    boundary=list(range(nx+1))+[j*row+nx for j in range(1,ny+1)]+[ny*row+i for i in range(nx-1,-1,-1)]+[j*row for j in range(ny-1,0,-1)]
    for n,a in enumerate(boundary):
        b=boundary[(n+1)%len(boundary)]
        faces.append((a,a+layer,b+layer,b))
    obj=mesh(name,verts,faces,mat,1)
    obj.location=loc
    obj.rotation_euler=(math.radians(24 if mat=='ochre' else 10),0,angle)
    pts=[]
    for a in boundary:
        p=Vector(verts[a]); p.z-=.007
        pts.append(p)
    piping=curve(name+' tailored seam',pts,.0015,'welt' if mat=='white' else 'thread',True)
    piping.location=loc
    piping.rotation_euler=obj.rotation_euler


def handle(name,x,y,z,length=.31):
    for sx in [-1,1]:
        rod(name+' standoff',(x+sx*length*.42,y+.024,z),(x+sx*length*.42,y-.014,z),.008,'black')
    rod(name+' horizontal bar',(x-length/2,y-.018,z),(x+length/2,y-.018,z),.009,'black')


def vase(name,loc,height,radius,mat,shape='round'):
    if shape=='tall':
        profile=[(.72*radius,0),(.85*radius,.025*height),(radius,.25*height),(.86*radius,.62*height),(.49*radius,.86*height),(.46*radius,.96*height),(.58*radius,height),(.48*radius,height),(.39*radius,.94*height),(.40*radius,.84*height),(.73*radius,.55*height),(.77*radius,.14*height),(.01,.12*height)]
    else:
        profile=[(.60*radius,0),(.82*radius,.03*height),(radius,.25*height),(.98*radius,.55*height),(.64*radius,.81*height),(.60*radius,.95*height),(.69*radius,height),(.57*radius,height),(.49*radius,.93*height),(.53*radius,.80*height),(.85*radius,.52*height),(.80*radius,.18*height),(.01,.12*height)]
    return lathe(name,loc,profile,mat,64)


def book(name,loc,dims,mat,angle=0):
    cover=.004
    pages=box(name+' paper block',(0,0,0),(dims[0]-.008,dims[1]-.009,dims[2]-cover*2),'paper',.002)
    parts=[pages]
    for z in [-dims[2]/2+cover/2,dims[2]/2-cover/2]:
        parts.append(box(name+' cover',(0,0,z),(dims[0],dims[1],cover),mat,.001))
    parts.append(box(name+' spine',(-dims[0]/2+.003,0,0),(.006,dims[1],dims[2]),mat,.002))
    for obj in parts:
        x,y,z=obj.location
        obj.location=(loc[0]+x*math.cos(angle)-y*math.sin(angle),loc[1]+x*math.sin(angle)+y*math.cos(angle),loc[2]+z)
        obj.rotation_euler[2]=angle


def globe_lamp(name,x,y,z):
    cylinder(name+' brass foot',(x,y,z+.012),.078,.024,'brass',.004)
    cylinder(name+' brass socket',(x,y,z+.065),.034,.10,'brass',.003)
    sphere(name+' frosted light bulb',(x,y,z+.122),(.028,.028,.052),'bulb',32,16)
    # Two concentric boundaries form an actual thin glass shell.
    globe=sphere(name+' clear glass globe',(x,y,z+.154),(.140,.140,.140),'glass',64,32)
    s=globe.modifiers.new('Blown glass wall 1.2 mm','SOLIDIFY')
    s.thickness=.0012
    light(name+' warm point','POINT',(x,y,z+.132),4.0,(1,.72,.40),size=.025)


def build_furniture():
    collection('05 | Six drawer walnut dresser')
    x,y=-2.45,1.39
    width,depth=1.45,.53
    # Recessed base and a six-drawer carcass with individual editable fronts.
    box('Dresser recessed plinth',(x,y,.095),(width-.14,depth-.10,.17),'walnutX',.007)
    for sx in [-1,1]:
        box('Dresser vertical side',(x+sx*(width/2-.024),y,.63),(.048,depth,1.13),'walnutZ',.007)
    box('Dresser dark inner carcass',(x,y+.016,.62),(width-.08,depth-.08,1.04),'walnutX',.005)
    box('Dresser overhanging top',(x,y,1.205),(width+.035,depth+.025,.045),'walnutX',.008)
    for row in range(3):
        for col in range(2):
            dx=x+(col-.5)*(width-.095)/2
            z=.29+row*.335
            front=y-depth/2-.012
            box(f'Dresser drawer {row*2+col+1} front',(dx,front,z),((width-.095)/2-.009,.042,.323),'walnutX',.004)
            handle(f'Dresser drawer {row*2+col+1} handle',dx,front-.035,z+.065,.34)
    # Matching square mirror, with real specular reflection.
    mz=2.08
    size=1.32
    box('Dresser square mirror glass',(x,1.807,mz),(size-.10,.012,size-.10),'mirror',.001)
    box('Mirror dark backing',(x,1.828,mz),(size,.035,size),'walnutX',.003)
    for sx in [-1,1]:
        box('Mirror vertical walnut frame',(x+sx*(size/2-.027),1.783,mz),(.055,.065,size),'walnutZ',.005)
    for sz in [-1,1]:
        box('Mirror horizontal walnut frame',(x,1.783,mz+sz*(size/2-.027)),(size,.065,.055),'walnutX',.005)
    collection('06 | Dresser styling and lamps')
    top=1.229
    book('Oatmeal design book',(x-.38,1.24,top+.016),(.43,.26,.032),'book2',-.04)
    book('Sage design book',(x-.40,1.25,top+.049),(.39,.235,.033),'book1',.025)
    book('Aubergine design book',(x-.35,1.255,top+.079),(.31,.21,.027),'book3',-.055)
    vase('Tall stoneware vase',(x-.46,1.54,top),.30,.073,'ceramic','tall')
    vase('Small fluted ochre pot',(x-.57,1.23,top+.096),.115,.07,'ceramic')
    for i in range(30):
        a=i*2*math.pi/30
        pts=[]
        for j in range(20):
            t=j/19
            r=.052+.017*math.sin(t*math.pi)
            pts.append((x-.57+r*math.cos(a),1.23+r*math.sin(a),top+.096+t*.109))
        curve('Pot vertical handmade flute',pts,.0015,'thread')
    globe_lamp('Globe lamp left',x+.12,1.38,top)
    globe_lamp('Globe lamp right',x+.47,1.37,top)
    collection('07 | Walnut nightstand')
    nx,ny=2.005,1.35
    for sx in [-1,1]:
        for sy in [-1,1]:
            box('Nightstand square leg',(nx+sx*.25,ny+sy*.20,.34),(.045,.045,.66),'walnutZ',.005)
    for sx in [-1,1]:
        box('Nightstand lower open frame side',(nx+sx*.25,ny,.055),(.045,.44,.045),'walnutY',.004)
    for sy in [-1,1]:
        box('Nightstand lower frame crossbar',(nx,ny+sy*.20,.055),(.54,.045,.045),'walnutX',.004)
    box('Nightstand open lower shelf',(nx,ny,.105),(.49,.365,.025),'walnutX',.004)
    for sx in [-1,1]:
        box('Nightstand drawer cabinet side',(nx+sx*.25,ny,.60),(.045,.45,.25),'walnutZ',.005)
    box('Nightstand drawer box',(nx,ny+.01,.60),(.46,.41,.22),'walnutX',.004)
    box('Nightstand single drawer front',(nx,ny-.233,.605),(.45,.038,.205),'walnutX',.004)
    handle('Nightstand drawer handle',nx,ny-.265,.63,.26)
    box('Nightstand walnut top',(nx,ny,.745),(.59,.49,.045),'walnutX',.007)
    vase('Olive ceramic bedside vase',(nx+.12,ny+.04,.768),.20,.085,'green')
    cylinder('Small walnut bedside trinket pot',(nx-.14,ny-.04,.798),.046,.06,'walnutZ',.005)
    # An understated small bottle in the gap to the left of the headboard.
    collection('08 | Small bedside ceramics')
    box('Left floating bedside ledge',(-.66,1.40,.59),(.33,.32,.035),'walnutX',.005)
    vase('Small cream water carafe',(-.67,1.41,.61),.25,.052,'ceramicwhite','tall')
    sphere('Carafe walnut stopper',(-.67,1.41,.88),(.031,.031,.031),'walnutZ',24,12)
    cylinder('Small bedside drinking cup',(-.80,1.36,.68),.027,.14,'ceramicwhite',.004)
    build_chair()
    build_ottoman_rug()


def build_chair():
    collection('09 | Dark timber occasional chair')
    M['chairwood']=wood('Espresso stained chair wood','Z')
    cr=next(n for n in M['chairwood'].node_tree.nodes if n.type=='VALTORGB')
    for el in cr.color_ramp.elements:
        el.color=tuple(c*.19 for c in el.color[:3])+(1,)
    cx,cy=-3.46,.48
    seat=cylinder('Chair shaped round seat',(cx,cy,.46),.24,.047,'chairwood',.015)
    seat.scale=(1,.92,1)
    for sx in [-1,1]:
        for sy in [-1,1]:
            rod('Chair tapered leg',(cx+sx*.18,cy+sy*.16,.45),(cx+sx*.22,cy+sy*.205,.02),.020,'chairwood')
    for sx in [-1,1]:
        rod('Chair back upright',(cx+sx*.18,cy+.15,.44),(cx+sx*.205,cy+.16,.99),.017,'chairwood')
    pts=[]
    for i in range(48):
        a=math.pi*i/47
        pts.append((cx+.26*math.cos(a),cy+.02+.20*math.sin(a),.98+.02*math.sin(a)))
    curve('Chair curved back rail',pts,.025,'chairwood')
    for i in range(5):
        x=cx-.14+i*.07
        rod('Chair back spindle',(x,cy+.19,.48),(x,cy+.19,.98),.008,'chairwood')


def build_ottoman_rug():
    collection('10 | Sculpted ivory area rug')
    rug=box('Ivory woven rug',(.0,-.51,.035),(4.85,3.58,.045),'rug',.065)
    # Fine irregular edge loops make the rug read as textile, not a slab.
    for edge in [-1,1]:
        pts=[(-2.35+i*4.7/160,-.51+edge*1.77,.057+.001*math.sin(i*2)) for i in range(161)]
        curve('Rug bound long edge',pts,.005,'welt')
    collection('11 | Cognac leather ottoman')
    x,y=.03,-1.25
    profile=[(.223,.065),(.247,.073),(.259,.10),(.267,.15),(.269,.37),(.265,.45),(.251,.48)]
    lathe('Ottoman supple leather body',(x,y,0),profile,'leather',96)
    cylinder('Ottoman recessed underside',(x,y,.064),.226,.024,'black',.008)
    # Lens-shaped cushion is a surface of revolution with no sharp cylinder rim.
    profile=[(.001,.479),(.18,.486),(.24,.482),(.261,.47),(.266,.455),(.259,.444),(.18,.449),(.001,.45)]
    lathe('Ottoman cushioned leather lid',(x,y,0),profile,'leather',96)
    for z,r in [(.457,.266),(.088,.25)]:
        pts=[(x+r*math.cos(i*2*math.pi/128),y+r*math.sin(i*2*math.pi/128),z) for i in range(128)]
        curve('Ottoman leather welt',pts,.0028,'leather',True)
    # Discrete stitches around the upper edge, visible in a close-up.
    for i in range(150):
        a=i*2*math.pi/150
        a1=a+.018
        r=.258
        curve('Ottoman saddle stitch',[(x+r*math.cos(a),y+r*math.sin(a),.475),(x+r*math.cos(a1),y+r*math.sin(a1),.475)],.00065,'leatherthread')
    curve('Ottoman vertical panel seam',[(x+.268*math.cos(-.9),y+.268*math.sin(-.9),.105+i*.33/30) for i in range(31)],.0012,'leatherthread')


def capsule_art(name,x,z,width,height,mat,y=1.796):
    # Flat cut-paper capsule: a closed silhouette lies on an actual framed canvas.
    r=width/2
    straight=height/2-r
    verts=[]
    for i in range(33):
        a=math.pi*i/32
        verts.append((x+r*math.cos(a),y,z+straight+r*math.sin(a)))
    for i in range(33):
        a=math.pi+math.pi*i/32
        verts.append((x+r*math.cos(a),y,z-straight+r*math.sin(a)))
    return mesh(name,verts,[tuple(range(len(verts)))],mat)


def build_art_lights():
    collection('12 | Framed geometric paper artworks')
    for idx,x in enumerate([.025,1.04]):
        z=2.425
        w,h=.70,1.03
        box(f'Artwork {idx+1} backing',(x,1.823,z),(w,.035,h),'walnutX',.003)
        box(f'Artwork {idx+1} paper',(x,1.798,z),(w-.055,.004,h-.055),'artpaper',0)
        for sx in [-1,1]:
            box('Artwork vertical walnut frame',(x+sx*(w/2-.012),1.773,z),(.025,.045,h),'walnutZ',.003)
        for sz in [-1,1]:
            box('Artwork horizontal walnut frame',(x,1.773,z+sz*(h/2-.012)),(w,.045,.025),'walnutX',.003)
        box('Geometric charcoal rectangle',(x+.145,1.791,z+.02),(.28,.003,.91),'artdark',0)
        capsule_art('Upper light capsule',x-.145,z+.12,.285,.72,'artlight',1.785)
        capsule_art('Lower pale capsule',x+.145,z-.16,.285,.57,'artpaper',1.781)
        box('Translucent-looking gray geometric band',(x,1.776,z-.08),(w-.06,.002,.18),'artgray',0)
    collection('13 | Architectural lamps')
    for idx,x in enumerate([-.60,1.86]):
        y,z=1.68,1.67
        cylinder('Sconce '+str(idx+1)+' wall rose',(x,1.814,z+.10),.065,.022,'black',.006,(math.pi/2,0,0))
        rod('Sconce bent arm',(x,1.79,z+.09),(x,1.63,z+.12),.009,'black')
        rod('Sconce shade neck',(x,1.63,z+.12),(x,1.58,z+.025),.012,'black')
        # Open hollow conical metal shade, with a warm inner material.
        profile=[(.092,0),(.091,.008),(.017,.17),(.012,.17),(.084,.008),(.085,0)]
        shade=lathe('Sconce '+str(idx+1)+' open black cone',(x,1.565,z-.12),profile,'black',64,False)
        shade.data.materials.append(M['shadeinside'])
        for p in shade.data.polygons:
            if p.index//64>=3:
                p.material_index=1
        sphere('Sconce concealed warm bulb',(x,1.565,z-.065),(.021,.021,.026),'bulb',24,12)
        lamp=light('Sconce '+str(idx+1)+' warm pool','AREA',(x,1.563,z-.112),7.5,(1,.72,.42),(x,1.83,.65),.11)
        lamp.data.shape='DISK'
    collection('14 | Daylight and photographic fill')
    world=bpy.data.worlds.new('Soft exterior sky')
    bpy.context.scene.world=world
    world.use_nodes=True
    bg=world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value=(.77,.84,1,1)
    bg.inputs['Strength'].default_value=.38
    camera_bg=world.node_tree.nodes.new('ShaderNodeBackground')
    camera_bg.inputs['Color'].default_value=(1,.97,.91,1)
    camera_bg.inputs['Strength'].default_value=1.5
    path=world.node_tree.nodes.new('ShaderNodeLightPath')
    mix=world.node_tree.nodes.new('ShaderNodeMixShader')
    world.node_tree.links.new(path.outputs['Is Camera Ray'],mix.inputs[0])
    world.node_tree.links.new(bg.outputs['Background'],mix.inputs[1])
    world.node_tree.links.new(camera_bg.outputs['Background'],mix.inputs[2])
    world.node_tree.links.new(mix.outputs[0],world.node_tree.nodes.get('World Output').inputs['Surface'])
    window_fill=light('Large soft window daylight','AREA',(-1.47,2.24,2.05),360,(1,.91,.76),(.6,-.7,.45),2.6)
    sun=light('Soft late-morning sun','SUN',(-3,4,5),1.4,(1,.88,.70),(1.0,-2.1,.1))
    sun.data.angle=math.radians(7)
    room_fill=light('Broad room bounce','AREA',(-1.5,-2.8,2.9),110,(1,.94,.84),(.4,.7,.6),4.0)
    ceiling_fill=light('Ceiling bounced skylight','AREA',(.5,.2,3.2),70,(.86,.91,1),(.5,.2,.0),3.0)
    for fill in [window_fill,room_fill,ceiling_fill]:
        fill.visible_camera=False
        fill.visible_glossy=False


def camera_and_settings():
    collection('15 | Camera')
    data=bpy.data.cameras.new('Bedroom architectural camera 46 mm')
    camera=bpy.data.objects.new('Camera | final composition',data)
    COLL.objects.link(camera)
    camera.location=(-2.0,-6.45,1.90)
    target=Vector((-.50,.53,1.22))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    data.lens=46
    data.sensor_width=36
    data.clip_start=.05
    data.clip_end=100
    focus=bpy.data.objects.new('Focus | front half of bed',None)
    COLL.objects.link(focus)
    focus.location=(.54,.10,.76)
    focus.empty_display_size=.12
    data.dof.use_dof=True
    data.dof.focus_object=focus
    data.dof.aperture_fstop=7.1
    data.dof.aperture_blades=7
    scene=bpy.context.scene
    scene.camera=camera
    scene.render.engine='CYCLES'
    scene.cycles.samples=96
    scene.cycles.use_denoising=True
    scene.cycles.use_adaptive_sampling=True
    scene.cycles.adaptive_threshold=.035
    scene.cycles.max_bounces=8
    scene.cycles.diffuse_bounces=4
    scene.cycles.glossy_bounces=4
    scene.cycles.transmission_bounces=8
    scene.cycles.transparent_max_bounces=8
    scene.cycles.sample_clamp_indirect=3
    scene.cycles.seed=SEED
    scene.render.resolution_x=1600
    scene.render.resolution_y=1128
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.image_settings.color_mode='RGB'
    scene.render.image_settings.color_depth='8'
    scene.render.film_transparent=False
    scene.render.threads_mode='FIXED'
    scene.render.threads=6
    scene.view_settings.view_transform='AgX'
    scene.view_settings.exposure=.35
    scene.unit_settings.system='METRIC'
    scene.unit_settings.length_unit='METERS'
    scene.render.filepath=str(ROOT/'bedroom-final.png')
    preferences=bpy.context.preferences.addons['cycles'].preferences
    preferences.refresh_devices()
    devices=[d for d in preferences.devices if d.type!='CPU']
    scene.cycles.device='GPU' if devices else 'CPU'
    for d in preferences.devices:
        d.use=(d in devices) if devices else d.type=='CPU'
    log('Render device: '+scene.cycles.device)
    # Opening the .blend immediately shows the composition in material mode.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=='VIEW_3D':
                area.spaces.active.region_3d.view_perspective='CAMERA'
                area.spaces.active.shading.type='MATERIAL'
    scene['reference_image']='Gemini_Generated_Image_w9q4niw9q4niw9q4.jpg'
    scene['construction']='Editable meshes, curves and self-contained procedural materials; no image-plane reconstruction.'
    scene['cloth_method']='Deterministic sculpted mesh drapes; no cloth simulation bake required.'


def save_scene():
    scene=bpy.context.scene
    scene.render.filepath=str(ROOT/'bedroom-final.png')
    scene.render.resolution_percentage=100
    scene.cycles.samples=96
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'bedroom.blend'))
    log('Saved editable scene: '+str(ROOT/'bedroom.blend'))


def render_preview():
    scene=bpy.context.scene
    scene.render.resolution_percentage=40
    scene.cycles.samples=20
    scene.cycles.adaptive_threshold=.10
    scene.render.filepath=str(ROOT/'bedroom-preview.png')
    log('Rendering preview')
    bpy.ops.render.render(write_still=True)
    log('Preview complete')


def render_final():
    scene=bpy.context.scene
    scene.render.resolution_percentage=100
    scene.cycles.samples=96
    scene.cycles.adaptive_threshold=.035
    scene.render.filepath=str(ROOT/'bedroom-final.png')
    # Save before rendering, so the complete editable scene is always retained.
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'bedroom.blend'))
    log('Rendering final 1600 x 1128')
    bpy.ops.render.render(write_still=True)
    log('Final complete')
    report={
        'blender_version':bpy.app.version_string,
        'objects':len(scene.objects),
        'mesh_objects':sum(o.type=='MESH' for o in scene.objects),
        'materials':len(bpy.data.materials),
        'collections':[c.name for c in scene.collection.children],
        'camera':scene.camera.name,
        'engine':scene.render.engine,
        'device':scene.cycles.device,
        'resolution':[scene.render.resolution_x,scene.render.resolution_y],
        'samples_max':scene.cycles.samples,
        'image_textures':len(bpy.data.images),
        'missing_external_images':[i.filepath for i in bpy.data.images if i.source=='FILE' and not i.packed_file and i.filepath and not Path(bpy.path.abspath(i.filepath)).exists()],
        'blend_file':str(ROOT/'bedroom.blend'),
        'final_render':str(ROOT/'bedroom-final.png'),
        'elapsed_this_run_seconds':round(time.time()-START,1),
    }
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


_base_materials = build_materials
_base_chair = build_chair
_base_ottoman = build_ottoman_rug
_base_settings = camera_and_settings


def wood(name, axis='X', oak=False):
    """Two grain scales and warped growth bands, varied between timber boards."""
    mat=material(name,'#65432C' if not oak else '#B79B73',.39)
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Coat Weight'].default_value=.08
    bs.inputs['Coat Roughness'].default_value=.42
    tc=node(mat,'ShaderNodeTexCoord')
    info=node(mat,'ShaderNodeObjectInfo')
    seed=node(mat,'ShaderNodeVectorMath'); seed.operation='SCALE'
    seed.inputs[0].default_value=(2.71,1.43,3.19)
    link(mat,info,'Random',seed,'Scale')
    add=node(mat,'ShaderNodeVectorMath'); add.operation='ADD'
    link(mat,tc,'Generated',add,0); link(mat,seed,'Vector',add,1)
    mapping=node(mat,'ShaderNodeVectorMath'); mapping.operation='MULTIPLY'
    mapping.inputs[1].default_value={'X':(.7,3.3,3.3),'Y':(3.3,.7,3.3),'Z':(3.3,3.3,.7)}[axis]
    link(mat,add,'Vector',mapping,0)
    wave=node(mat,'ShaderNodeTexWave','Warped walnut growth rings')
    wave.wave_type='BANDS'
    wave.bands_direction='Y' if axis=='X' else 'X'
    wave.inputs['Scale'].default_value=2.0
    wave.inputs['Distortion'].default_value=11
    wave.inputs['Detail'].default_value=3
    wave.inputs['Detail Scale'].default_value=.52
    wave.inputs['Detail Roughness'].default_value=.62
    link(mat,mapping,'Vector',wave,'Vector')
    grainmap=node(mat,'ShaderNodeVectorMath'); grainmap.operation='MULTIPLY'
    grainmap.inputs[1].default_value={'X':(.75,65,12),'Y':(65,.75,12),'Z':(28,35,.55)}[axis]
    link(mat,add,'Vector',grainmap,0)
    noise=node(mat,'ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value=2.6
    noise.inputs['Detail'].default_value=2.5
    link(mat,grainmap,'Vector',noise,'Vector')
    blend=node(mat,'ShaderNodeMixRGB'); blend.blend_type='MIX'
    blend.inputs[0].default_value=.72
    link(mat,wave,'Fac',blend,1); link(mat,noise,'Fac',blend,2)
    colors=[(0,'#A18864'),(.25,'#BAA17D'),(.6,'#CDB58F'),(1,'#D6C19F')] if oak else [(0,'#3C281D'),(.20,'#4B3325'),(.48,'#63452F'),(.75,'#78563B'),(1,'#896748')]
    cr=ramp(mat,colors)
    link(mat,blend,'Color',cr,'Fac'); link(mat,cr,'Color',bs,'Base Color')
    bump=node(mat,'ShaderNodeBump'); bump.inputs['Strength'].default_value=.18
    bump.inputs['Distance'].default_value=.0006
    link(mat,noise,'Fac',bump,'Height'); link(mat,bump,'Normal',bs,'Normal')
    return mat


def fabric(name,color,coarse=False):
    mat=material(name,color,.88)
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Sheen Weight'].default_value=.12 if not coarse else .20
    bs.inputs['Specular IOR Level'].default_value=.22
    tc=node(mat,'ShaderNodeTexCoord')
    fiber=node(mat,'ShaderNodeTexNoise')
    fiber.inputs['Scale'].default_value=420 if coarse else 700
    fiber.inputs['Detail'].default_value=2
    link(mat,tc,'Object',fiber,'Vector')
    weave=node(mat,'ShaderNodeTexWave')
    weave.wave_type='BANDS'; weave.bands_direction='X'
    weave.inputs['Scale'].default_value=160 if coarse else 290
    weave.inputs['Distortion'].default_value=2
    link(mat,tc,'Object',weave,'Vector')
    mix=node(mat,'ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'
    mix.inputs[0].default_value=.45
    link(mat,weave,'Fac',mix,1); link(mat,fiber,'Fac',mix,2)
    bump=node(mat,'ShaderNodeBump')
    bump.inputs['Distance'].default_value=.0007 if coarse else .00035
    bump.inputs['Strength'].default_value=.30
    link(mat,mix,'Color',bump,'Height'); link(mat,bump,'Normal',bs,'Normal')
    return mat


def build_materials():
    _base_materials()
    M['white']=fabric('Cotton duvet | soft natural white','#EFEAE1')
    M['sheet']=fabric('White pillow cotton','#E6E0D6')
    M['ochre']=fabric('Mustard linen | reference ochre','#A47A2D',True)
    M['bolster']=fabric('Ochre corduroy bolster','#8F6C2C',True)
    M['throw']=fabric('Golden ochre coarse throw','#A67C32',True)
    M['thread']=material('Ochre woven stitch','#AE8C4B',.9)
    for key in ['walnutX','walnutY','walnutZ']:
        for n in M[key].node_tree.nodes:
            if n.type=='VALTORGB':
                for el in n.color_ramp.elements:
                    el.color=tuple(c*.65 for c in el.color[:3])+(1,)
    M['mortar']=plaster('Beige lime mortar | narrow soft joints','#C5B59C',125,.0015)
    M['wall']=plaster('Warm plaster on left wall','#D2C7B5',100,.0013)
    M['brick']=[plaster('Irregular limewashed beige brick '+str(i),c,100,.0035) for i,c in enumerate(['#B6A58D','#BDAE94','#BAAA90','#C3B29B','#B7A58C','#BDAE96'])]
    for mat in M['brick']:
        bs=mat.node_tree.nodes.get('Principled BSDF')
        tc=node(mat,'ShaderNodeTexCoord')
        noise=node(mat,'ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value=25
        noise.inputs['Detail'].default_value=3.5
        link(mat,tc,'Object',noise,'Vector')
        b=node(mat,'ShaderNodeBump'); b.inputs['Distance'].default_value=.003
        b.inputs['Strength'].default_value=.45
        previous=bs.inputs['Normal'].links[0].from_node
        link(mat,noise,'Fac',b,'Height'); link(mat,previous,'Normal',b,'Normal')
        link(mat,b,'Normal',bs,'Normal')
    M['leather']=material('Warm cognac leather','#78482B',.40)
    bs=M['leather'].node_tree.nodes.get('Principled BSDF')
    tex=node(M['leather'],'ShaderNodeTexNoise')
    tex.inputs['Scale'].default_value=155; tex.inputs['Detail'].default_value=3
    b=node(M['leather'],'ShaderNodeBump'); b.inputs['Distance'].default_value=.0008
    b.inputs['Strength'].default_value=.25
    link(M['leather'],tex,'Fac',b,'Height'); link(M['leather'],b,'Normal',bs,'Normal')
    M['rug']=fabric('Ivory wool rug | quiet irregular waves','#D7CDB9',True)
    mat=M['rug']; bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Sheen Weight'].default_value=.5
    tc=node(mat,'ShaderNodeTexCoord')
    mp=node(mat,'ShaderNodeVectorMath'); mp.operation='ADD'; mp.inputs[1].default_value=(1.8,1.5,0)
    link(mat,tc,'Object',mp,0)
    wave=node(mat,'ShaderNodeTexWave')
    wave.wave_type='RINGS'; wave.rings_direction='Z'
    wave.inputs['Scale'].default_value=4.5; wave.inputs['Distortion'].default_value=3.5
    wave.inputs['Detail Scale'].default_value=.6
    link(mat,mp,'Vector',wave,'Vector')
    b=node(mat,'ShaderNodeBump'); b.inputs['Strength'].default_value=.24
    b.inputs['Distance'].default_value=.0016
    previous=bs.inputs['Normal'].links[0].from_node
    link(mat,previous,'Normal',b,'Normal'); link(mat,wave,'Fac',b,'Height')
    link(mat,b,'Normal',bs,'Normal')
    M['rugfiber']=fabric('Loose ivory wool fibers','#D5CBB7',True)


def build_room():
    collection('01 | Reference room architecture')
    box('Floor foundation',(1,-1,-.055),(8,7.8,.09),'mortar',0)
    width=.18
    for column in range(46):
        x=-2.95+column*width
        y=-4.7-(column%3)*.43
        row=0
        while y<2.0:
            length=1.3+random.uniform(-.2,.2)
            lo=max(y,-4.7); hi=min(y+length,2.0)
            if hi>lo:
                box(f'Oak floorboard {column:02d}.{row:02d}',(x,(lo+hi)/2,-.009),(width-.0015,hi-lo-.002,.025),'oak',.001)
            y+=length; row+=1
    wx0,wx1=-2.265,-1.125
    wz0,wz1=.10,2.46
    back=1.98
    for a,b in [(-2.37,wx0),(wx1,4.7)]:
        box('Rear lime mortar substrate',((a+b)/2,back,1.75),(b-a,.16,3.5),'mortar',0)
    box('Window header',((wx0+wx1)/2,back,(wz1+3.5)/2),(wx1-wx0,.16,3.5-wz1),'mortar',0)
    box('Window sill substrate',((wx0+wx1)/2,back,wz0/2),(wx1-wx0,.16,wz0),'mortar',0)
    # Narrow, shallow joints and rough limewashed surfaces match the reference.
    bh=.0515
    for row in range(63):
        z=.027+row*.0557
        x=-2.55-(row%2)*.12; col=0
        while x<4.7:
            bw=.245+random.uniform(-.022,.024)
            lo=max(-2.37,x); hi=min(4.7,x+bw)
            intervals=[(lo,hi)]
            if z+bh/2>wz0 and z-bh/2<wz1:
                intervals=[(lo,min(hi,wx0)),(max(lo,wx1),hi)]
            for a,b in intervals:
                if b-a>.018:
                    ob=box(f'Handmade brick {row:02d}.{col:02d}.{a:.2f}',((a+b)/2,1.902+random.uniform(-.001,.001),z+random.uniform(-.0008,.0008)),(b-a,.018,bh+random.uniform(-.0015,.0015)),random.choice(M['brick']),.0028)
                    ob.rotation_euler[1]=random.uniform(-.006,.006)
            x+=bw+.0035; col+=1
    box('Left warm plaster wall',(-2.41,-1.3,1.75),(.16,6.6,3.5),'wall',0)
    box('Ceiling',(1,.15,3.55),(7,3.8,.1),'wall',0)
    box('Left subtle baseboard',(-2.313,-1.15,.06),(.028,6.2,.11),'wall',.003)
    for a,b in [(-2.37,wx0),(wx1,4.7)]:
        box('Rear subtle baseboard',((a+b)/2,1.858,.056),(b-a,.03,.105),'mortar',.003)
    mid=(wz0+wz1)/2
    for x in [wx0-.025,wx1+.025]:
        box('Window white vertical reveal',(x,1.91,mid),(.09,.31,wz1-wz0+.16),'ceramicwhite',.005)
    for z in [wz0-.035,wz1+.035]:
        box('Window white horizontal reveal',((wx0+wx1)/2,1.91,z),(wx1-wx0,.31,.09),'ceramicwhite',.005)
    box('Window projecting white sill',((wx0+wx1)/2,1.79,wz0-.06),(1.35,.45,.055),'ceramicwhite',.005)
    for x in [wx0+.025,wx1-.025]:
        box('Slim inner window sash',(x,2.05,mid),(.028,.035,wz1-wz0-.03),'ceramicwhite',.002)
    for z in [wz0+.03,wz1-.03]:
        box('Slim inner window rail',((wx0+wx1)/2,2.05,z),(wx1-wx0-.025,.035,.028),'ceramicwhite',.002)


def frame_rect(name,x,y,bottom,top,width,bar,depth):
    # Butt joints stop at the rails: no overlapping coplanar corner faces.
    inside=width-2*bar
    for sx in [-1,1]:
        box(name+' upright',(x+sx*(width/2-bar/2),y,(bottom+top)/2),(bar,depth,top-bottom),'walnutZ',.004)
    for z in [bottom+bar/2,top-bar/2]:
        box(name+' horizontal',(x,y,z),(inside-.001,depth,bar),'walnutX',.004)


def duvet_point(u,v):
    x=(1.16 if u<0 else 1.065)*u
    y=-.780+1.615*v+.009*math.sin(9*u+2*v)+.005*math.sin(21*u-3*v)
    side=max(0,min(1,(abs(x)-.79)/(.37 if u<0 else .275)))
    front=max(0,min(1,(-.65-y)/.13))
    drop_side=(.57+.14*(1-v)**2)*math.sin(side*math.pi/2)**1.5
    drop_front=.34*math.sin(front*math.pi/2)**1.5
    crown=.065*(1-u*u)*math.sin(.2+v*2.4)
    z=.800+crown-max(drop_side,drop_front)-.07*min(drop_side,drop_front)
    z+=.008*math.sin(12*u+7*v)+.004*math.sin(31*u-15*v)+.003*math.sin(65*u+19*v)
    z+=side**1.3*(.007*math.sin(29*v+5*u)+.003*math.sin(67*v-3*u))
    # Localized tension folds leave the broad cotton surface naturally calm.
    for center,slope,amp,width in [(.17,.15,.018,.034),(.31,-.12,.014,.026),(.52,.20,.020,.04),(.72,-.10,.013,.028)]:
        z+=amp*math.exp(-((v-center-slope*u)/width)**2)*(.25+.75*abs(u))
    z+=.010*front*math.sin(30*u+2*v)
    # Wrinkles displace perpendicular to the hanging fabric, not only vertically.
    # This gives the front and side drapes real folds instead of a flat curtain.
    y+=front**.8*(.014*math.sin(19*u+.6)+.008*math.sin(43*u+1.2)+.015)
    x+=math.copysign(1,u)*side**.8*(.018*math.sin(16*v+.3*math.sin(8*v))+.006*math.sin(43*v+u)) if u else 0
    return (.54+x,y,z)


def surface_grid(name,func,nx,ny,mat,thickness=.012,sub=1):
    vertices=[func(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
    faces=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
    ob=mesh(name,vertices,faces,mat,sub)
    if thickness:
        solid=ob.modifiers.new('Soft textile loft','SOLIDIFY'); solid.thickness=thickness; solid.offset=-.3
    return ob


def build_bed():
    cx=.54
    collection('03 | Reference walnut bed frame')
    frame_rect('Headboard',cx,1.52,.045,1.28,1.88,.065,.07)
    frame_rect('Footboard',cx,-.84,.045,.57,1.88,.063,.075)
    box('Headboard wide walnut infill',(cx,1.526,.93),(1.744,.052,.55),'walnutX',.004)
    box('Footboard walnut infill',(cx,-.825,.337),(1.75,.050,.235),'walnutX',.004)
    for x in [cx-.85,cx+.85]:
        box('Long walnut bed side rail',(x,.34,.315),(.065,2.24,.15),'walnutY',.005)
    for i in range(13):
        box('Timber mattress support',(cx,-.66+i*.164,.42),(1.65,.073,.028),'walnutX',.002)
    collection('04 | Reference cotton bedding')
    box('Queen mattress | 160 x 200 cm',(cx,.34,.575),(1.60,2,.32),'sheet',.10)
    for z in [.445,.702]:
        pts=[]
        for i in range(160):
            a=i*2*math.pi/160
            pts.append((cx+.79*math.copysign(abs(math.cos(a))**.22,math.cos(a)),.34+.99*math.copysign(abs(math.sin(a))**.22,math.sin(a)),z))
        curve('Mattress stitched edge',pts,.0017,'welt',True)
    surface_grid('Duvet | sculpted cotton drape',lambda u,v:duvet_point(2*u-1,v),144,184,'white',.028,1)
    for side in [-1,1]:
        curve('Duvet hem stitching',[duvet_point(side,j/184) for j in range(185)],.0015,'welt')
    curve('Duvet front bound hem',[duvet_point(-1+2*i/144,0) for i in range(145)],.002,'welt')
    # The folded-over upper edge has thickness and a broad, softly rolled lip.
    def cuff(u,v):
        x,y,z=duvet_point(2*u-1,.84+.16*v)
        return (x,y-.014,z+.010+.022*math.sin(math.pi*v)**.8)
    surface_grid('Duvet folded upper cuff',cuff,144,20,'white',.018,1)
    build_pillow('White pillow left',(cx-.39,1.095,.815),(.77,.49,.18),'sheet',-.045)
    build_pillow('White pillow right',(cx+.39,1.11,.82),(.77,.49,.18),'sheet',.035)
    build_pillow('Mustard pillow left',(cx-.39,1.16,.968),(.79,.50,.24),'ochre',-.055)
    build_pillow('Mustard pillow right',(cx+.39,1.16,.968),(.79,.50,.24),'ochre',.035)
    profile=[(.001,-.69),(.065,-.69),(.092,-.679),(.103,-.65),(.104,.65),(.092,.679),(.065,.69),(.001,.69)]
    bol=lathe('Ochre ribbed bolster',(0,0,0),profile,'bolster',96)
    bol.rotation_euler[1]=math.pi/2; bol.location=(cx,.88,.845)
    for i in range(152):
        x=cx-.66+i*1.32/151
        curve('Bolster corduroy rib',[(x,.88+.105*math.cos(a*2*math.pi/48),.845+.105*math.sin(a*2*math.pi/48)) for a in range(48)],.0012,'thread',True)
    for sx in [-1,1]:
        curve('Bolster end piping',[(cx+sx*.68,.88+.09*math.cos(a*2*math.pi/64),.845+.09*math.sin(a*2*math.pi/64)) for a in range(64)],.0017,'thread',True)
    def throwpoint(u,v):
        xlocal=-1.065+1.265*u
        y=-.38+.38*v+.075*math.sin(3*u)+.018*math.sin(9*u+5*v)
        q=duvet_point(xlocal/1.065,(y+.780)/1.615)
        return (q[0],y,q[2]+.024+.011*math.sin(29*u+3*v)+.006*math.sin(16*v+6*u)+.022*math.exp(-((v-.75)/.12)**2))
    surface_grid('Mustard throw | casually folded linen',throwpoint,100,42,'throw',.008,1)
    for side in [0,1]:
        curve('Throw stitched long hem',[throwpoint(i/100,side) for i in range(101)],.0015,'thread')
    for j in range(76):
        p=throwpoint(1,j/75)
        curve('Golden throw fringe',[p,(p[0]+.012,p[1]-.004,p[2]-.004),(p[0]+.035+random.random()*.017,p[1]+random.uniform(-.005,.005),p[2]-.012-random.random()*.015)],.0008,'thread')


def build_pillow(name,loc,dims,mat,angle):
    nx,ny=56,36
    vertices=[]
    for side in [1,-1]:
        for j in range(ny+1):
            v=-1+2*j/ny
            for i in range(nx+1):
                u=-1+2*i/nx
                x=dims[0]/2*u*(1-.035*abs(v)**10)
                y=dims[1]/2*v*(1-.055*abs(u)**10)
                puff=max(0,(1-u**6)*(1-v**6))**.46
                wrinkle=.0035*math.sin(35*u+9*v)*(abs(u)**8+abs(v)**8)*puff
                z=side*(.004+dims[2]/2*puff+wrinkle)
                z+=.006*math.sin(3*u+2*v)*(1-u*u)*(1-v*v)
                vertices.append((x,y,z))
    row=nx+1; layer=row*(ny+1); faces=[]
    for k,side in enumerate([1,-1]):
        for j in range(ny):
            for i in range(nx):
                a=k*layer+j*row+i
                f=(a,a+1,a+row+1,a+row)
                faces.append(f if side==1 else tuple(reversed(f)))
    boundary=list(range(nx+1))+[j*row+nx for j in range(1,ny+1)]+[ny*row+i for i in range(nx-1,-1,-1)]+[j*row for j in range(ny-1,0,-1)]
    for i,a in enumerate(boundary):
        b=boundary[(i+1)%len(boundary)]; faces.append((a,a+layer,b+layer,b))
    obj=mesh(name,vertices,faces,mat,1); obj.location=loc
    obj.rotation_euler=(math.radians(7),0,angle)
    seam=curve(name+' perimeter seam',[(vertices[a][0],vertices[a][1],0) for a in boundary],.0013,'thread' if mat=='ochre' else 'welt',True)
    seam.location=loc; seam.rotation_euler=obj.rotation_euler


def transform_collection(coll,transform):
    bpy.context.view_layer.update()
    for obj in coll.objects:
        obj.matrix_world=transform@obj.matrix_world


def build_furniture():
    coll=collection('05 | Reference dresser on left wall')
    w,d=1.45,.53
    box('Dresser recessed plinth',(0,0,.074),(w-.08,d-.06,.13),'walnutX',.004)
    for sx in [-1,1]:
        box('Dresser walnut side',(sx*(w/2-.019),0,.55),(.038,d,.91),'walnutZ',.004)
    box('Dresser rear panel',(0,d/2-.018,.55),(w-.076,.035,.91),'walnutX',.003)
    box('Dresser interior',(0,.01,.55),(w-.08,d-.075,.90),'walnutX',.004)
    box('Dresser walnut top',(0,0,1.015),(w+.035,d+.025,.035),'walnutX',.005)
    for row in range(3):
        for col in range(2):
            x=(col-.5)*.69
            z=.265+row*.289
            y=-d/2-.008
            box(f'Dresser drawer {row*2+col+1} front',(x,y,z),(.681,.035,.279),'walnutX',.003)
            handle(f'Dresser drawer {row*2+col+1} handle',x,y-.029,z+.066,.32)
    tr=Matrix.Translation(Vector((-2.02,.70,0)))@Matrix.Rotation(math.pi/2,4,'Z')
    transform_collection(coll,tr)
    # The mirror is square; its lower portion is occluded by the dresser.
    coll=collection('06 | Square mirror on left plaster wall')
    size=1.30; mz=1.49; bar=.045
    box('Dresser square mirror glass',(0,-.012,mz),(size-.078,.004,size-.078),'mirror',0)
    box('Mirror dark backing',(0,.010,mz),(size,.025,size),'walnutX',.002)
    for sx in [-1,1]:
        box('Mirror vertical walnut frame',(sx*(size/2-bar/2),-.025,mz),(bar,.054,size),'walnutZ',.003)
    for sz in [-1,1]:
        box('Mirror horizontal walnut frame',(0,-.025,mz+sz*(size/2-bar/2)),(size-2*bar-.001,.054,bar),'walnutX',.003)
    transform_collection(coll,Matrix.Translation(Vector((-2.26,.70,0)))@Matrix.Rotation(math.pi/2,4,'Z'))
    coll=collection('07 | Dresser ceramics books and glass lamps')
    top=1.033
    book('Oatmeal design book',(-.38,-.09,top+.016),(.43,.26,.032),'book2',-.04)
    book('Sage design book',(-.40,-.08,top+.049),(.39,.235,.033),'book1',.025)
    book('Aubergine design book',(-.35,-.075,top+.079),(.31,.21,.027),'book3',-.055)
    vase('Tall stoneware vase',(-.46,.13,top),.30,.073,'ceramic','tall')
    vase('Small ochre decorative pot',(-.56,-.1,top+.096),.115,.070,'ceramic')
    for i in range(30):
        a=i*2*math.pi/30
        pts=[]
        for j in range(20):
            t=j/19; radius=.052+.017*math.sin(t*math.pi)
            pts.append((-.56+radius*math.cos(a),-.1+radius*math.sin(a),top+.096+t*.109))
        curve('Stoneware vertical flute',pts,.0012,'thread')
    globe_lamp('Globe lamp left',.12,-.01,top)
    globe_lamp('Globe lamp right',.47,-.02,top)
    transform_collection(coll,tr)
    collection('08 | Reference open frame walnut nightstand')
    x,y=1.80,1.35
    for sx in [-1,1]:
        for sy in [-1,1]:
            box('Nightstand slender upright',(x+sx*.245,y+sy*.195,.335),(.038,.038,.62),'walnutZ',.003)
    for sx in [-1,1]:
        box('Nightstand lower frame side',(x+sx*.245,y,.047),(.038,.35,.038),'walnutY',.003)
    for sy in [-1,1]:
        box('Nightstand lower crossbar',(x,y+sy*.195,.047),(.45,.038,.038),'walnutX',.003)
    for sx in [-1,1]:
        box('Nightstand drawer side',(x+sx*.235,y,.545),(.045,.43,.205),'walnutZ',.003)
    box('Nightstand interior back',(x,y+.195,.545),(.43,.035,.20),'walnutX',.003)
    box('Nightstand drawer box',(x,y+.005,.505),(.43,.39,.14),'walnutX',.003)
    box('Nightstand single drawer front',(x,y-.222,.515),(.43,.032,.155),'walnutX',.003)
    handle('Nightstand dark bar handle',x,y-.253,.545,.24)
    box('Nightstand walnut top',(x,y,.671),(.57,.47,.034),'walnutX',.004)
    vase('Olive ceramic bedside vase',(x+.095,y+.025,.69),.19,.078,'green')
    cylinder('Walnut bedside trinket pot',(x-.14,y-.04,.717),.043,.055,'walnutZ',.004)
    collection('09 | Left bedside ceramic bottles')
    box('Left bedside ledge',(-.83,1.40,.59),(.31,.31,.029),'walnutX',.004)
    vase('Cream water carafe',(-.77,1.45,.606),.24,.048,'ceramicwhite','tall')
    sphere('Walnut carafe stopper',(-.77,1.45,.865),(.029,.029,.029),'walnutZ',24,12)
    cylinder('Cream ceramic cup',(-.94,1.37,.671),.025,.13,'ceramicwhite',.003)
    _base_chair()
    transform_collection(COLL,Matrix.Translation(Vector((1.44,-.84,0))))
    build_ottoman_rug()


def build_ottoman_rug():
    collection('11 | Reference ivory wool rug')
    box('Ivory woven rug',(.44,-.12,.024),(3.90,3.30,.036),'rug',.026)
    for sy in [-1,1]:
        curve('Rug woven bound edge',[(-1.48+i*3.84/180,-.12+sy*1.638,.041) for i in range(181)],.0023,'welt')
    # A single batched object holds sparse millimeter-scale wool fuzz.
    data=bpy.data.curves.new('Fine wool nap','CURVE'); data.dimensions='3D'
    data.bevel_depth=.00022; data.bevel_resolution=0; data.resolution_u=1
    for i in range(10500):
        x=random.uniform(-1.49,2.37); y=random.uniform(-1.75,1.51)
        a=random.random()*2*math.pi; h=random.uniform(.002,.005)
        sp=data.splines.new('POLY'); sp.points.add(1)
        sp.points[0].co=(x,y,.041,1)
        sp.points[1].co=(x+.001*math.cos(a),y+.001*math.sin(a),.041+h,1)
    nap=bpy.data.objects.new('Rug fine wool fibers',data); COLL.objects.link(nap); assign(nap,'rugfiber')
    collection('12 | Reference cognac leather ottoman')
    x,y=1.14,-1.25
    profile=[(.212,.055),(.234,.063),(.244,.09),(.248,.14),(.247,.46),(.239,.53)]
    lathe('Ottoman supple leather body',(x,y,0),profile,'leather',112)
    cylinder('Ottoman recessed underside',(x,y,.048),.215,.014,'black',.004)
    profile=[(.001,.552),(.16,.557),(.227,.552),(.243,.54),(.247,.527),(.24,.516),(.16,.524),(.001,.525)]
    lathe('Ottoman softly cushioned lid',(x,y,0),profile,'leather',112)
    curve('Ottoman leather lid piping',[(x+.244*math.cos(i*2*math.pi/160),y+.244*math.sin(i*2*math.pi/160),.531) for i in range(160)],.0022,'leather',True)
    for i in range(170):
        a=i*2*math.pi/170; b=a+.015
        curve('Ottoman top saddle stitch',[(x+.239*math.cos(a),y+.239*math.sin(a),.545),(x+.239*math.cos(b),y+.239*math.sin(b),.545)],.00055,'leatherthread')
    curve('Ottoman vertical stitched join',[(x+.248*math.cos(-1.1),y+.248*math.sin(-1.1),.08+j*.43/40) for j in range(41)],.0007,'leatherthread')


def build_art_lights():
    collection('13 | Reference geometric framed prints')
    for name,col in [('artpaper','#B5AFA5'),('artgray','#918A80'),('artdark','#69645F'),('artlight','#BCB7AE')]:
        M[name]=material('Reference print '+name,col,.95)
    for index,x in enumerate([.025,.818]):
        z=1.94; w,h=.54,.80; bar=.020
        box(f'Artwork {index+1} backing',(x,1.864,z),(w,.022,h),'walnutX',.002)
        box(f'Artwork {index+1} paper',(x,1.847,z),(w-.035,.002,h-.035),'artpaper',0)
        for sx in [-1,1]:
            box('Print vertical walnut trim',(x+sx*(w/2-bar/2),1.844,z),(bar,.035,h),'walnutZ',.002)
        for sz in [-1,1]:
            box('Print horizontal walnut trim',(x,1.844,z+sz*(h/2-bar/2)),(w-2*bar-.001,.035,bar),'walnutX',.002)
        box('Print graphite field',(x+.114,1.8452,z+.013),(.222,.0003,.758),'artdark',0)
        if index==0:
            capsule_art('Left print upper capsule',x-.118,z+.09,.225,.59,'artlight',1.8447)
            capsule_art('Left print lower capsule',x+.116,z-.07,.225,.63,'artpaper',1.8444)
        else:
            capsule_art('Right print tall capsule',x-.119,z+.038,.225,.66,'artlight',1.8447)
            capsule_art('Right print lower oval',x+.116,z-.18,.228,.27,'artpaper',1.8444)
        box('Print muted horizontal band',(x,1.8440,z-.033),(w-.040,.0002,.135),'artgray',0)
    collection('14 | Warm practical lamps')
    for i,x in enumerate([-.82,1.71]):
        cylinder(f'Sconce {i+1} wall rose',(x,1.851,1.39),.055,.023,'black',.004,(math.pi/2,0,0))
        rod('Sconce bent brass-black arm',(x,1.84,1.397),(x,1.67,1.408),.008,'black')
        rod('Sconce short neck',(x,1.67,1.408),(x,1.643,1.378),.009,'black')
        profile=[(.083,0),(.083,.005),(.014,.160),(.009,.160),(.077,.005),(.078,0)]
        shade=lathe(f'Sconce {i+1} open black cone',(x,1.633,1.225),profile,'black',72,False)
        shade.data.materials.append(M['shadeinside'])
        for face in shade.data.polygons:
            if face.index//72>=3: face.material_index=1
        sphere('Sconce warm concealed bulb',(x,1.633,1.266),(.019,.019,.023),'bulb',24,12)
        lamp=light(f'Sconce {i+1} warm downward pool','SPOT',(x,1.633,1.222),12,(1,.66,.33),(x,1.875,.71),.035)
        lamp.data.spot_size=math.radians(85); lamp.data.spot_blend=.7
    collection('15 | Reference daylight')
    world=bpy.data.worlds.new('Soft warm room and white exterior'); bpy.context.scene.world=world; world.use_nodes=True
    bg=world.node_tree.nodes.get('Background'); bg.inputs['Color'].default_value=(.80,.87,1,1); bg.inputs['Strength'].default_value=.23
    camera_bg=world.node_tree.nodes.new('ShaderNodeBackground')
    camera_bg.inputs['Color'].default_value=(1,.98,.92,1); camera_bg.inputs['Strength'].default_value=10
    path=world.node_tree.nodes.new('ShaderNodeLightPath')
    mix=world.node_tree.nodes.new('ShaderNodeMixShader')
    world.node_tree.links.new(path.outputs['Is Camera Ray'],mix.inputs[0])
    world.node_tree.links.new(bg.outputs['Background'],mix.inputs[1])
    world.node_tree.links.new(camera_bg.outputs['Background'],mix.inputs[2])
    world.node_tree.links.new(mix.outputs[0],world.node_tree.nodes.get('World Output').inputs['Surface'])
    window=light('Soft daylight at real window','AREA',(-1.69,2.20,1.28),260,(1,.93,.83),(-1.69,0,1.28),1)
    window.data.shape='RECTANGLE'; window.data.size=1.10; window.data.size_y=2.36
    sun=light('Warm sun through left window','SUN',(-3,6,5),1.6,(1,.89,.74),(2,-3,0))
    sun.data.angle=math.radians(8)
    # This broad photographic fill sits behind the camera and outside reflections.
    fill=light('Low energy camera-side bounce','AREA',(4.9,-6.9,3),65,(1,.95,.87),(.3,.7,.75),4.0)
    fill.data.specular_factor=.15
    fill=light('Soft left-front window bounce','AREA',(2.8,-2.5,3.5),300,(1,.95,.87),(.55,.15,.7),3.0)
    fill.data.specular_factor=.3


def camera_and_settings():
    _base_settings()
    scene=bpy.context.scene; camera=scene.camera
    yaw=-.48572569724028625
    camera.location=(4.492448614959805,-6.147171702482923,1.1345267465643862)
    direction=Vector((math.sin(yaw),math.cos(yaw),0))
    camera.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    camera.data.name='Reference-calibrated architectural lens'
    camera.data.lens=61.17557509641382
    camera.data.shift_x=.5-.6614159937673988
    camera.data.shift_y=(.41618250195304834-.5)/(1600/1128)
    camera.data.dof.aperture_fstop=8
    camera.data.dof.focus_object.location=(.7,-.10,.8)
    scene.view_settings.exposure=0
    scene.cycles.samples=96
    scene.cycles.adaptive_threshold=.035
    scene['reference_revision']='v2: calibrated right-side camera, left-wall dresser, natural walnut and sculpted duvet.'
    # Record the actual Blender projection to verify calibration conventions.
    from bpy_extras.object_utils import world_to_camera_view
    bpy.context.view_layer.update()
    pts=[(-.4,1.52,1.28),(1.48,1.52,1.28),(-.4,-.84,.57),(1.48,-.84,.57)]
    projected=[]
    for p in pts:
        q=world_to_camera_view(scene,camera,Vector(p)); projected.append([round(q.x,5),round(1-q.y,5)])
    log('Reference bed-corner projection: '+str(projected))


_v2_materials = build_materials
_v2_bed = build_bed
_v2_room = build_room
_v2_ottoman = build_ottoman_rug
_v2_camera = camera_and_settings
_v2_art_lights = build_art_lights
_v2_pillow = build_pillow


def packed_image(asset, channel):
    path=ROOT/'textures'/f'{asset}_{channel}.jpg'
    # Packed images keep the .blend portable. The same files accompany the builder.
    image=bpy.data.images.load(str(path),check_existing=True)
    image.colorspace_settings.name='sRGB' if channel=='Diffuse' else 'Non-Color'
    image.pack()
    return image


def pbr_surface(mat, asset, axis='X', leather=False):
    bs=mat.node_tree.nodes.get('Principled BSDF')
    tc=node(mat,'ShaderNodeTexCoord')
    sep=node(mat,'ShaderNodeSeparateXYZ'); comb=node(mat,'ShaderNodeCombineXYZ')
    link(mat,tc,'UV',sep,0)
    order='XYZ'  # Per-object UVs already align the grain to the timber axis.
    for dest,source in zip('XYZ',order): link(mat,sep,source,comb,dest)
    vec=comb
    if leather:
        scale=node(mat,'ShaderNodeVectorMath'); scale.operation='SCALE'; scale.inputs['Scale'].default_value=1
        link(mat,comb,0,scale,0); vec=scale
    else:
        info=node(mat,'ShaderNodeObjectInfo')
        seed=node(mat,'ShaderNodeVectorMath'); seed.operation='SCALE'; seed.inputs[0].default_value=(.61,.39,.27)
        link(mat,info,'Random',seed,'Scale')
        offset=node(mat,'ShaderNodeVectorMath'); offset.operation='ADD'
        link(mat,comb,0,offset,0); link(mat,seed,0,offset,1); vec=offset
    maps={}
    for channel in ['Diffuse','nor_gl','Rough']:
        tex=node(mat,'ShaderNodeTexImage',f'CC0 Poly Haven | {asset} | {channel}')
        tex.image=packed_image(asset,channel); tex.projection='FLAT'
        link(mat,vec,0,tex,'Vector'); maps[channel]=tex
    tint=node(mat,'ShaderNodeMixRGB','Warm furniture finish over photographed grain')
    tint.blend_type='MULTIPLY'; tint.inputs[0].default_value=1
    tint.inputs[2].default_value=(.55,.36,.22,1) if not leather else (1.05,.90,.80,1)
    link(mat,maps['Diffuse'],'Color',tint,1); link(mat,tint,'Color',bs,'Base Color')
    normal=node(mat,'ShaderNodeNormalMap','Photographed OpenGL tangent-space normal')
    normal.inputs['Strength'].default_value=.6 if leather else .35
    link(mat,maps['nor_gl'],'Color',normal,'Color')
    pores=node(mat,'ShaderNodeBump','Photographed grain / leather pores')
    pores.inputs['Strength'].default_value=.32 if leather else .23
    pores.inputs['Distance'].default_value=.0012 if leather else .0006
    link(mat,maps['Diffuse'],'Color',pores,'Height'); link(mat,normal,'Normal',pores,'Normal'); link(mat,pores,'Normal',bs,'Normal')
    rough=node(mat,'ShaderNodeMapRange')
    rough.inputs['From Min'].default_value=.05; rough.inputs['From Max'].default_value=.9
    rough.inputs['To Min'].default_value=.42 if leather else .31
    rough.inputs['To Max'].default_value=.65 if leather else .49
    link(mat,maps['Rough'],'Color',rough,'Value'); link(mat,rough,'Result',bs,'Roughness')
    bs.inputs['Coat Weight'].default_value=.035 if leather else .09
    bs.inputs['Coat Roughness'].default_value=.48
    mat['pbr_source']=f'https://polyhaven.com/a/{asset}'
    mat['license']='CC0'


def textile_detail(mat, coarse=False):
    bs=mat.node_tree.nodes.get('Principled BSDF')
    tc=node(mat,'ShaderNodeTexCoord')
    waves=[]
    for direction in ['X','Y']:
        wave=node(mat,'ShaderNodeTexWave','Individual warp / weft threads')
        wave.wave_type='BANDS'; wave.bands_direction=direction
        wave.inputs['Scale'].default_value=125 if coarse else 285
        wave.inputs['Distortion'].default_value=.65
        wave.inputs['Detail Scale'].default_value=1.6
        link(mat,tc,'Object',wave,'Vector'); waves.append(wave)
    cross=node(mat,'ShaderNodeMixRGB'); cross.blend_type='MULTIPLY'; cross.inputs[0].default_value=1
    link(mat,waves[0],'Fac',cross,1); link(mat,waves[1],'Fac',cross,2)
    bump=node(mat,'ShaderNodeBump','Cross-woven thread relief in real meters')
    bump.inputs['Strength'].default_value=.58 if coarse else .42
    bump.inputs['Distance'].default_value=.0011 if coarse else .00045
    link(mat,cross,'Color',bump,'Height'); link(mat,bump,'Normal',bs,'Normal')
    variation=node(mat,'ShaderNodeTexNoise','Subtle yarn dye variation')
    variation.inputs['Scale'].default_value=42; variation.inputs['Detail'].default_value=3
    link(mat,tc,'Object',variation,'Vector')
    tone=node(mat,'ShaderNodeMixRGB'); tone.blend_type='MULTIPLY'; tone.inputs[0].default_value=.16
    tone.inputs[1].default_value=bs.inputs['Base Color'].default_value
    link(mat,variation,'Fac',tone,2); link(mat,tone,0,bs,'Base Color')
    bs.inputs['Sheen Weight'].default_value=.28 if coarse else .17
    bs.inputs['Sheen Roughness'].default_value=.72
    bs.inputs['Roughness'].default_value=.82


def build_materials():
    _v2_materials()
    for axis in 'XYZ': pbr_surface(M['walnut'+axis],'natural_walnut_veneer',axis)
    pbr_surface(M['leather'],'brown_leather',leather=True)
    for key in ['white','sheet','ochre','throw','bolster','welt']:
        textile_detail(M[key],key in ['ochre','throw','bolster'])
    bs=M['black'].node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=rgba('#191714')
    bs.inputs['Metallic'].default_value=.25; bs.inputs['Roughness'].default_value=.45
    for mat in M['brick']:
        bs=mat.node_tree.nodes.get('Principled BSDF')
        tc=node(mat,'ShaderNodeTexCoord')
        n=node(mat,'ShaderNodeTexNoise'); n.inputs['Scale'].default_value=64; n.inputs['Detail'].default_value=4
        link(mat,tc,'Object',n,'Vector')
        mix=node(mat,'ShaderNodeMixRGB'); mix.blend_type='MULTIPLY'; mix.inputs[0].default_value=.18
        mix.inputs[1].default_value=bs.inputs['Base Color'].default_value
        link(mat,n,'Fac',mix,2); link(mat,mix,0,bs,'Base Color')
    mat=M['rug']; bs=mat.node_tree.nodes.get('Principled BSDF')
    wave=next(n for n in mat.node_tree.nodes if n.type=='TEX_WAVE' and n.wave_type=='RINGS')
    wave.inputs['Scale'].default_value=3.5
    tone=node(mat,'ShaderNodeMixRGB'); tone.blend_type='MULTIPLY'; tone.inputs[0].default_value=.19
    tone.inputs[1].default_value=rgba('#DED5C4')
    link(mat,wave,'Fac',tone,2); link(mat,tone,0,bs,'Base Color')
    bump=bs.inputs['Normal'].links[0].from_node
    bump.inputs['Strength'].default_value=.5; bump.inputs['Distance'].default_value=.0035


def build_room():
    _v2_room()
    # Actual uneven masonry relief complements the two shader bump scales.
    texture=bpy.data.textures.new('Handmade brick surface irregularity',type='CLOUDS')
    texture.noise_scale=.027; texture.noise_depth=2
    for ob in bpy.context.scene.objects:
        if not ob.name.startswith('Handmade brick'): continue
        sub=ob.modifiers.new('Fine masonry surface grid','SUBSURF'); sub.subdivision_type='SIMPLE'; sub.levels=1
        disp=ob.modifiers.new('Millimeter handmade brick relief','DISPLACE')
        disp.texture=texture; disp.texture_coords='GLOBAL'; disp.strength=.0028; disp.mid_level=.5
        ob.location.y+=random.uniform(-.0015,.0015)


def duvet_point(u,v):
    x=(1.12 if u<0 else 1.065)*u
    y=-.780+1.615*v+.008*math.sin(9*u+2*v)+.005*math.sin(21*u-3*v)
    side=max(0,min(1,(abs(x)-.79)/(.33 if u<0 else .275)))
    front=max(0,min(1,(-.65-y)/.13))
    drop_side=(.47+.09*(1-v)**2)*math.sin(side*math.pi/2)**1.35
    drop_front=.32*math.sin(front*math.pi/2)**1.4
    crown=.078*(1-u*u)*math.sin(.35+v*2.4)
    z=.806+crown-max(drop_side,drop_front)-.035*min(drop_side,drop_front)
    z+=.043*math.exp(-((v-.72+.10*u)/.075)**2)*(1-.3*u*u)
    # Broad, asymmetric loft, not a flat mathematical sheet.
    z+=.013*math.sin(7*u+5*v)+.009*math.sin(13*u-8*v)*math.cos(6*v)
    z+=.0035*math.sin(48*u+23*v)+.002*math.sin(91*u-42*v)
    for center,slope,amp,width in [(.15,.08,.030,.027),(.29,-.11,.021,.024),(.46,.16,.025,.035),(.64,-.13,.018,.022),(.79,.05,.021,.033)]:
        q=(v-center-slope*u)/width
        z+=amp*(math.exp(-q*q)-.28*math.exp(-((q-1.7)/1.4)**2))*(.28+.72*abs(u))
    # Small tension wrinkles fan out from the side and foot edges.
    z+=.009*(abs(u)**3)*math.sin(69*v+13*u)*math.sin(19*v+3*u)
    z+=.005*front*math.sin(48*u+2*v)
    y+=front**.8*(.020*math.sin(21*u+.6)+.008*math.sin(49*u+1.2)+.016)
    if u:
        x+=math.copysign(1,u)*side**.75*(.023*math.sin(15*v+.6*math.sin(8*v))+.010*math.sin(41*v+u)+.004*math.sin(87*v))
    return (.54+x,y,z)


def build_pillow(name,loc,dims,mat,angle):
    _v2_pillow(name,loc,dims,mat,angle)
    ob=bpy.data.objects.get(name)
    # Pinched corner creases and a shallow center compression are sculpted into
    # both mesh patches, so the same detail survives GLB export.
    for vert in ob.data.vertices:
        u=vert.co.x/(dims[0]/2); v=vert.co.y/(dims[1]/2)
        if vert.co.z>0:
            crease=0
            for sx in [-1,1]:
                for sy in [-1,1]:
                    edge=math.exp(-((u-sx*.80)/.16)**2-((v-sy*.76)/.25)**2)
                    crease+=edge*(.007+.004*math.sin(32*u-19*v))
            vert.co.z-=crease
            vert.co.z+=.004*math.sin(17*u+11*v)*abs(v)**5


def build_bed():
    _v2_bed()
    collection('04b | Fine cotton tailoring')
    for i in range(215):
        a=-.97+1.94*i/215; b=a+.0044
        p=duvet_point(a,.014); q=duvet_point(b,.014)
        curve('Duvet double needle hem stitch',[(p[0],p[1]-.0008,p[2]+.0015),(q[0],q[1]-.0008,q[2]+.0015)],.00038,'welt')
    # Move the bolster slightly forward so its ribbing reads above the cuff.
    for ob in bpy.context.scene.objects:
        if ob.name.startswith(('Ochre ribbed bolster','Bolster corduroy rib','Bolster end piping')):
            ob.location.y-=.025; ob.location.z+=.014


def build_ottoman_rug():
    _v2_ottoman()
    collection('12b | Leather tailoring details')
    x,y=1.14,-1.25
    # Two stitch rows and an indented seam, with separate visible thread dashes.
    for row in [-1,1]:
        for j in range(95):
            z=.082+j*.0045; a=-1.1+row*.012
            curve('Ottoman double saddle stitch',[(x+.2485*math.cos(a),y+.2485*math.sin(a),z),(x+.2485*math.cos(a),y+.2485*math.sin(a),z+.0024)],.00036,'leatherthread')
    body=bpy.data.objects.get('Ottoman supple leather body')
    sub=body.modifiers.new('Soft upholstered side continuity','SUBSURF'); sub.levels=1
    for vert in body.data.vertices:
        dx=vert.co.x-x; dy=vert.co.y-y; radius=math.hypot(dx,dy)
        if radius>.23:
            a=math.atan2(dy,dx)
            d=.0008*math.sin(13*a+vert.co.z*17)+.0012*math.sin(31*a)*math.exp(-((vert.co.z-.12)/.08)**2)
            vert.co.x+=d*dx/radius; vert.co.y+=d*dy/radius


def build_art_lights():
    _v2_art_lights()
    M['artgray'].node_tree.nodes.get('Principled BSDF').inputs['Alpha'].default_value=.20
    # Expose the warm pools of both sconces, rather than a broad glossy fill.
    for ob in bpy.context.scene.objects:
        if ob.type=='LIGHT' and ob.data.type=='SPOT': ob.data.energy*=2.6
    bpy.data.objects['Soft left-front window bounce'].data.energy=215
    bpy.data.objects['Soft left-front window bounce'].data.size=3.5


def add_pbr_uvs():
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or not any(m and m.get('pbr_source') for m in ob.data.materials): continue
        data=ob.data
        uv=data.uv_layers.active or data.uv_layers.new(name='PBR grain orientation')
        lo=[min(v.co[a] for v in data.vertices) for a in range(3)]
        hi=[max(v.co[a] for v in data.vertices) for a in range(3)]
        span=[max(hi[a]-lo[a],.0001) for a in range(3)]
        center=Vector(((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,0))
        for poly in data.polygons:
            mat=data.materials[poly.material_index]
            if not mat or not mat.get('pbr_source'): continue
            normal_axis=max(range(3),key=lambda a:abs(poly.normal[a]))
            leather='brown_leather' in mat['pbr_source']
            grain={'X':0,'Y':1,'Z':2}.get(mat.name[-1],0)
            axes=([a for a in range(3) if a!=normal_axis] if grain==normal_axis else [grain,next(a for a in range(3) if a!=normal_axis and a!=grain)])
            angles=[]
            if leather and normal_axis!=2:
                angles=[math.atan2(data.vertices[data.loops[i].vertex_index].co.y-center.y,data.vertices[data.loops[i].vertex_index].co.x-center.x)/(2*math.pi) for i in poly.loop_indices]
                if max(angles)-min(angles)>.5: angles=[a+1 if a<0 else a for a in angles]
            for j,i in enumerate(poly.loop_indices):
                co=data.vertices[data.loops[i].vertex_index].co
                if leather:
                    value=((angles[j]*2*math.pi*.248/.4,co.z/.4) if angles else ((co.x-center.x)/.4,(co.y-center.y)/.4))
                else:
                    value=((co[axes[0]]-lo[axes[0]])/span[axes[0]],(co[axes[1]]-lo[axes[1]])/span[axes[1]])
                uv.data[i].uv=value


def camera_and_settings():
    add_pbr_uvs()
    _v2_camera()
    scene=bpy.context.scene
    scene.render.resolution_x=7680; scene.render.resolution_y=5416
    scene.cycles.samples=32; scene.cycles.adaptive_min_samples=8
    scene.cycles.adaptive_threshold=.065
    scene.cycles.max_bounces=6; scene.cycles.diffuse_bounces=3
    scene.cycles.glossy_bounces=3; scene.cycles.transmission_bounces=6
    scene.cycles.use_denoising=True
    scene.cycles.denoiser='OPENIMAGEDENOISE'
    scene.cycles.denoising_input_passes='RGB_ALBEDO_NORMAL'
    scene.render.image_settings.color_depth='8'
    scene.camera.data.dof.aperture_fstop=11
    scene.render.use_persistent_data=True
    scene['reference_revision']='v3: commercial 8K; photographed walnut/leather, cross-woven fabric, plush sculpted folds, uneven masonry and leather stitching.'
    scene['texture_credits']='Poly Haven CC0: Natural Walnut Veneer, Brown Leather. See texture source URLs and bundled credits.'


def save_scene():
    scene=bpy.context.scene
    scene.render.resolution_percentage=100
    scene.render.filepath=str(ROOT/'bedroom-final-8k.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'bedroom.blend'))
    log('Saved portable, editable 8K scene')


def render_preview():
    scene=bpy.context.scene
    scene.render.resolution_percentage=16
    scene.cycles.samples=24; scene.cycles.adaptive_threshold=.08
    scene.render.filepath=str(ROOT/'bedroom-preview.png')
    log('Rendering material / geometry proof at 1228 pixels')
    bpy.ops.render.render(write_still=True)
    log('Preview complete')


def render_final():
    scene=bpy.context.scene
    scene.render.resolution_percentage=100
    scene.cycles.samples=32; scene.cycles.adaptive_threshold=.065
    scene.render.filepath=str(ROOT/'bedroom-final-8k.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'bedroom.blend'))
    log('Rendering native 7680 x 5416 pixels with Cycles / OIDN')
    bpy.ops.render.render(write_still=True)
    report={'revision':'v3','blender_version':bpy.app.version_string,'objects':len(scene.objects),'mesh_objects':sum(o.type=='MESH' for o in scene.objects),'materials':len(bpy.data.materials),'resolution':[7680,5416],'native_render':True,'engine':scene.render.engine,'samples_max':scene.cycles.samples,'denoiser':scene.cycles.denoiser,'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'elapsed_this_run_seconds':round(time.time()-START,1)}
    (ROOT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    log('Native 8K render complete')


def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',choices=['preview','final','all','build'],default='all')
    config=parser.parse_args(args)
    ROOT.mkdir(parents=True,exist_ok=True)
    if config.stage=='final':
        if Path(bpy.data.filepath).resolve()!=ROOT/'bedroom.blend':
            bpy.ops.wm.open_mainfile(filepath=str(ROOT/'bedroom.blend'))
        render_final()
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    log('Building materials')
    build_materials()
    log('Building architecture')
    build_room()
    log('Building bed and sculpted textiles')
    build_bed()
    log('Building furniture and decorative objects')
    build_furniture()
    build_art_lights()
    camera_and_settings()
    save_scene()
    if config.stage in {'preview','all'}:
        render_preview()
    if config.stage=='all':
        render_final()
    log(f'Finished stage {config.stage}; {len(bpy.context.scene.objects)} editable objects')


if __name__=='__main__':
    main()

