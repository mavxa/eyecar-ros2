#!/usr/bin/env python3
"""Build an editable visual URDF and CAD references from dimensions.json."""

import argparse
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = ROOT / 'models/eyecar/dimensions.json'
BLACK = (0.08, 0.09, 0.10, 1)
SILVER = (0.67, 0.70, 0.73, 1)
BLUE = (0.04, 0.29, 0.57, 1)
GREEN = (0.08, 0.42, 0.22, 1)


def camera_center_z(d):
    return (d['chassis_bottom_z']+d['upper_plate_offset']+
            d['mast_height']+d['bracket_height']/2)


def rotation(rpy):
    r, p, y = rpy
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return ((cy*cp, cy*sp*sr-sy*cr, cy*sp*cr+sy*sr),
            (sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr), (-sp, cp*sr, cp*cr))


def transform(point, center, rpy):
    matrix = rotation(rpy)
    return tuple(sum(row[i] * point[i] for i in range(3)) + offset
                 for row, offset in zip(matrix, center))


def parts_for(d):
    parts = []

    def box(name, center, size, color=BLACK, rpy=(0, 0, 0), link='base_link'):
        parts.append(dict(name=name, kind='box', center=center, size=size,
                          color=color, rpy=rpy, link=link))

    def cylinder(name, center, radius, length, color=SILVER, rpy=(0, 0, 0), link='base_link'):
        parts.append(dict(name=name, kind='cylinder', center=center, size=(radius, length),
                          color=color, rpy=rpy, link=link))

    lower = d['chassis_bottom_z']
    middle = lower + d['electronics_plate_offset']
    upper = lower + d['upper_plate_offset']
    for name, z, color in [('electronics_plate', middle, BLACK),
                           ('upper_plate', upper, (0.15, 0.18, 0.20, 0.48))]:
        box(name, (0, 0, z), (d['plate_length'], d['plate_width'], d['plate_thickness']), color)
    for x in (-0.10, 0.10):
        for y in (-0.045, 0.045):
            cylinder(f'post_{x}_{y}', (x, y, (upper+middle)/2), 0.003,
                     upper-middle, SILVER)
            cylinder(f'lower_post_{x}_{y}', (x, y, (middle+lower)/2), 0.003,
                     middle-lower, SILVER)
    for y in (-0.035, 0.035):
        box(f'lower_rail_{y}', (0, y, lower+0.005), (0.205, 0.009, 0.010))
    box('transmission', (-0.03, 0, 0.033), (0.075, 0.045, 0.025), BLACK)
    cylinder('motor', (-0.045, 0.035, 0.037), 0.012, 0.045, SILVER, (0, math.pi/2, 0))
    cylinder('drive_shaft', (0, 0, 0.035), 0.003, d['wheelbase'], SILVER, (0, math.pi/2, 0))
    for x in (-d['wheelbase']/2, d['wheelbase']/2):
        cylinder(f'axle_{x}', (x, 0, d['wheel_radius']), 0.004, d['wheel_track'], SILVER, (math.pi/2, 0, 0))

    for end, x in [('rear', -d['wheelbase']/2), ('front', d['wheelbase']/2)]:
        for side, sign in [('left', 1), ('right', -1)]:
            y, z = sign*d['wheel_track']/2, d['wheel_radius']
            link = f'{end}_{side}_wheel'
            cylinder(link+'_tire', (x, y, z), d['wheel_radius'], d['wheel_width'], BLACK, (math.pi/2, 0, 0), link)
            cylinder(link+'_rim', (x, y, z), 0.018, d['wheel_width']+0.001, SILVER, (math.pi/2, 0, 0), link)
            cylinder(link+'_hub', (x, y, z), 0.006, d['wheel_width']+0.003, BLACK, (math.pi/2, 0, 0), link)
            for i in range(16):
                angle = i*math.tau/16
                box(link+f'_tread_{i}',
                    (x+(d['wheel_radius']-0.001)*math.sin(angle), y,
                     z+(d['wheel_radius']-0.001)*math.cos(angle)),
                    (0.008, d['wheel_width']+0.002, 0.003),
                    (0.13, 0.14, 0.15, 1), (0, angle, 0), link)

    box('raspberry_pi', (-0.057, 0, middle+0.008), (0.085, 0.056, 0.003), GREEN)
    for y in (-0.018, 0.018):
        box(f'pi_usb_{y}', (-0.020, y, middle+0.017), (0.016, 0.015, 0.014), SILVER)
    box('pi_chip', (-0.060, 0, middle+0.012), (0.016, 0.016, 0.004), BLACK)
    box('arduino_mega', (0.050, 0, middle+0.008), (0.102, 0.054, 0.003), BLUE)
    box('expansion_shield', (0.050, 0, middle+0.019), (0.090, 0.053, 0.003), (0.15, 0.20, 0.24, 1))
    for y in (-0.023, 0.023):
        box(f'headers_{y}', (0.050, y, middle+0.024), (0.085, 0.005, 0.008))

    bumper_x = d['plate_length']/2 + d['bumper_length']/2
    box('front_bumper', (bumper_x, 0, lower+0.003), (d['bumper_length'], d['bumper_width'], 0.006))
    for i, y in enumerate((-0.045, -0.015, 0.015, 0.045)):
        box(f'ir_{i}_board', (bumper_x-0.002, y, lower-0.003), (0.018, 0.010, 0.002), BLUE)
        box(f'ir_{i}_receiver', (bumper_x+0.003, y, lower-0.006), (0.006, 0.006, 0.004))

    for sensor in d['sensors']:
        name = sensor['name']
        angle = math.radians(sensor['yaw_deg'])
        origin = (sensor['x'], sensor['y'], sensor['z'])
        mount_z = middle+0.004
        box(f'us_{name}_bracket', (sensor['x']-0.003*math.cos(angle),
                                 sensor['y']-0.003*math.sin(angle), mount_z),
            (0.008,0.040,0.010),BLACK,(0,0,angle))
        box(f'us_{name}_pcb', origin, (0.002, 0.045, 0.020), BLUE, (0, 0, angle))
        for index, y in enumerate((-0.012, 0.012)):
            center = transform((0.007, y, 0), origin, (0, 0, angle))
            cylinder(f'us_{name}_{index}', center, 0.008, 0.012, SILVER, (0, math.pi/2, angle))

    mast_x = d['plate_length']/2-d['mast_from_front']
    mast_top = upper+d['mast_height']
    box('camera_mast', (mast_x, 0, upper+d['mast_height']/2),
        (0.004, d['mast_width'], d['mast_height']), BLACK)
    box('mast_foot', (mast_x, 0, upper+0.004), (0.025, 0.065, 0.006), BLACK)
    for y in (-d['bracket_width']/2, d['bracket_width']/2):
        box(f'camera_holder_{y}', (mast_x, y, mast_top+d['bracket_height']/2),
            (0.020, 0.004, d['bracket_height']), BLACK)
    box('camera_holder_bar', (mast_x, 0, mast_top+0.003), (0.025, d['bracket_width'], 0.006))
    camera_z = camera_center_z(d)
    box('camera_bar', (mast_x+0.010, 0, camera_z),
        (d['camera_depth'], d['camera_width'], d['camera_height']), (0.12, 0.14, 0.16, 1))
    cylinder('camera_lens_ring', (mast_x+0.010+d['camera_depth']/2, 0, camera_z),
             0.010, 0.006, SILVER, (0, math.pi/2, 0))
    cylinder('camera_lens', (mast_x+0.015+d['camera_depth']/2, 0, camera_z),
             0.007, 0.004, (0.02, 0.08, 0.12, 1), (0, math.pi/2, 0))
    return parts


def vector(values):
    return ' '.join(f'{value:.7g}' for value in values)


def make_urdf(d, parts):
    robot = ET.Element('robot', name='eyecar_visual')
    links = {'base_link': ET.SubElement(robot, 'link', name='base_link')}
    origins = {'base_link': (0, 0, 0)}

    def joint(name, parent, child, xyz, kind='fixed', axis=None, rpy=(0, 0, 0)):
        links[child] = ET.SubElement(robot, 'link', name=child)
        element = ET.SubElement(robot, 'joint', name=name, type=kind)
        ET.SubElement(element, 'parent', link=parent)
        ET.SubElement(element, 'child', link=child)
        ET.SubElement(element, 'origin', xyz=vector(xyz), rpy=vector(rpy))
        if axis:
            ET.SubElement(element, 'axis', xyz=axis)
        if kind == 'revolute':
            center = math.radians(d['estimated_max_steering_deg'])
            radius = d['wheelbase']/math.tan(center)
            limit = math.atan(d['wheelbase']/(radius-d['wheel_track']/2))
            ET.SubElement(element, 'limit', lower=str(-limit), upper=str(limit), effort='1', velocity='3')

    for end, x in [('rear', -d['wheelbase']/2), ('front', d['wheelbase']/2)]:
        for side, sign in [('left', 1), ('right', -1)]:
            name = f'{end}_{side}'
            xyz = (x, sign*d['wheel_track']/2, d['wheel_radius'])
            parent = 'base_link'
            if end == 'front':
                parent = name+'_steer_link'
                joint(name+'_steering', 'base_link', parent, xyz, 'revolute', '0 0 1')
            joint(name+'_wheel_joint', parent, name+'_wheel',
                  (0, 0, 0) if end == 'front' else xyz, 'continuous', '0 1 0')
            origins[name+'_wheel'] = xyz

    for sensor in d['sensors']:
        joint('us_'+sensor['name']+'_mount', 'base_link', 'us_'+sensor['name'],
              (sensor['x'], sensor['y'], sensor['z']), rpy=(0, 0, math.radians(sensor['yaw_deg'])))
    joint('camera_mount', 'base_link', 'camera_link',
          (d['plate_length']/2-d['mast_from_front']+0.010, 0,
           camera_center_z(d)))
    joint('camera_optical_mount', 'camera_link', 'camera_optical_frame', (0, 0, 0),
          rpy=(-math.pi/2, 0, -math.pi/2))

    for part in parts:
        local = tuple(a-b for a, b in zip(part['center'], origins[part['link']]))
        # Jazzy RViz can reuse the first material for all visuals of one link.
        # A fixed child per part preserves the different board, metal and rubber colors.
        part_link = 'part_'+part['name'].replace('-','m').replace('.','p')
        joint(part_link+'_mount',part['link'],part_link,local,rpy=part['rpy'])
        visual = ET.SubElement(links[part_link], 'visual', name=part['name'])
        ET.SubElement(visual, 'origin', xyz='0 0 0', rpy='0 0 0')
        geometry = ET.SubElement(visual, 'geometry')
        if part['kind'] == 'box':
            ET.SubElement(geometry, 'box', size=vector(part['size']))
        else:
            ET.SubElement(geometry, 'cylinder', radius=str(part['size'][0]), length=str(part['size'][1]))
        material = ET.SubElement(visual, 'material', name=part['name']+'_material')
        ET.SubElement(material, 'color', rgba=vector(part['color']))
    ET.indent(robot)
    return '<?xml version="1.0"?>\n'+ET.tostring(robot, encoding='unicode')+'\n'


def mesh(part):
    if part['kind'] == 'box':
        x, y, z = (v/2 for v in part['size'])
        vertices = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                    (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
        faces = [(0,2,1),(0,3,2),(4,5,6),(4,6,7),(0,1,5),(0,5,4),
                 (1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)]
    else:
        radius, length = part['size']
        count = 24
        vertices = [(radius*math.cos(i*math.tau/count), radius*math.sin(i*math.tau/count), z)
                    for z in (-length/2, length/2) for i in range(count)]
        vertices += [(0, 0, -length/2), (0, 0, length/2)]
        faces = []
        for i in range(count):
            j = (i+1) % count
            faces.extend([(i,j,j+count),(i,j+count,i+count),
                          (2*count,j,i),(2*count+1,i+count,j+count)])
    vertices = [transform(point, part['center'], part['rpy']) for point in vertices]
    return vertices, faces


def convex_hull(points):
    points = sorted(set(points))
    def cross(o,a,b):
        return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    sides = []
    for ordered in (points,list(reversed(points))):
        side = []
        for point in ordered:
            while len(side)>1 and cross(side[-2],side[-1],point)<=0:
                side.pop()
            side.append(point)
        sides.append(side[:-1])
    return sides[0]+sides[1]


def export_cad(output, d, parts):
    scad = ['// EyeCar visual reference; dimensions in mm. Not manufacturing geometry.', '$fn=32;']
    triangles = []
    for part in parts:
        center = vector([v*1000 for v in part['center']]).replace(' ', ',')
        angles = vector([math.degrees(v) for v in part['rpy']]).replace(' ', ',')
        prefix = f"// {part['name']}\ncolor([{','.join(map(str,part['color']))}]) translate([{center}]) rotate([{angles}]) "
        if part['kind'] == 'box':
            primitive = 'cube(['+','.join(str(v*1000) for v in part['size'])+'], center=true);'
        else:
            primitive = f"cylinder(r={part['size'][0]*1000},h={part['size'][1]*1000},center=true);"
        scad.append(prefix+primitive)
        vertices, faces = mesh(part)
        triangles.extend([[tuple(value*1000 for value in vertices[i]) for i in face] for face in faces])
    (output/'eyecar.scad').write_text('\n'.join(scad)+'\n')
    with (output/'eyecar.stl').open('wb') as stream:
        stream.write(b'EyeCar visual assembly, units mm, overlapping components'.ljust(80, b' '))
        stream.write(struct.pack('<I', len(triangles)))
        for triangle in triangles:
            a = [triangle[1][i]-triangle[0][i] for i in range(3)]
            b = [triangle[2][i]-triangle[0][i] for i in range(3)]
            normal = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
            length = math.sqrt(sum(value*value for value in normal)) or 1
            stream.write(struct.pack('<12fH', *(v/length for v in normal),
                                     *(v for point in triangle for v in point), 0))

    # DXF R12 with orthographic silhouettes and explicit dimension references.
    entities = []
    def line(a, b, layer='MODEL'):
        entities.append(f'0\nLINE\n8\n{layer}\n10\n{a[0]}\n20\n{a[1]}\n30\n0\n11\n{b[0]}\n21\n{b[1]}\n31\n0\n')
    def text(x, y, value, height=4):
        entities.append(f'0\nTEXT\n8\nDIMENSIONS\n10\n{x}\n20\n{y}\n30\n0\n40\n{height}\n1\n{value}\n')
    for axes, offset, title in [((0,1),(170,110),'TOP'), ((0,2),(170,300),'SIDE'), ((1,2),(480,300),'FRONT')]:
        for part in parts:
            if '_tread_' in part['name']:
                continue
            vertices,_ = mesh(part)
            outline = convex_hull([(point[axes[0]]*1000+offset[0],point[axes[1]]*1000+offset[1]) for point in vertices])
            for i,point in enumerate(outline):
                line(point,outline[(i+1)%len(outline)])
        text(offset[0]-100, offset[1]-100, title, 6)
    def dimension(a, b, label):
        line(a,b,'DIMENSIONS')
        for point in (a,b):
            line((point[0]-2,point[1]-2),(point[0]+2,point[1]+2),'DIMENSIONS')
        text((a[0]+b[0])/2+3,(a[1]+b[1])/2+3,label)
    length,width = d['plate_length']*1000,d['plate_width']*1000
    bottom = d['chassis_bottom_z']*1000
    middle,upper = bottom+d['electronics_plate_offset']*1000,bottom+d['upper_plate_offset']*1000
    camera_z = camera_center_z(d)*1000
    camera_width = d['camera_width']*1000
    dimension((170-length/2,110+width/2+45),(170+length/2,110+width/2+45),f'PLATES {length:g}')
    dimension((170-length/2-15,110-width/2),(170-length/2-15,110+width/2),f'{width:g}')
    dimension((35,300+bottom),(35,300+upper),f'STACK {upper-bottom:g}')
    dimension((65,300+middle),(65,300+upper),f'GAP {upper-middle:g}')
    dimension((80,300+bottom),(80,300+middle),f'GAP {middle-bottom:g}')
    dimension((480-camera_width/2,300+camera_z+30),(480+camera_width/2,300+camera_z+30),f'CAMERA {camera_width:g}')
    text(40,710,'EYECAR - APPROXIMATE VISUAL MODEL / mm',7)
    text(40,695,f"Plates {length:g}x{width:g}, wheels R{d['wheel_radius']*1000:g}, stack {upper-bottom:g}")
    text(40,685,f"Camera {camera_width:g}x{d['camera_height']*1000:g}; mast {d['mast_height']*1000:g} high")
    text(40,675,f"Wheelbase {d['wheelbase']*1000:g} and track {d['wheel_track']*1000:g} are estimates. Verify before manufacturing.")
    header = '0\nSECTION\n2\nHEADER\n9\n$ACADVER\n1\nAC1009\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n'
    (output/'eyecar drawing.dxf').write_text(header+''.join(entities)+'0\nENDSEC\n0\nEOF\n')


def preview(output, d, parts):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    figure = plt.figure(figsize=(11, 9), facecolor='white')
    axes = figure.add_subplot(111, projection='3d')
    for part in parts:
        vertices, faces = mesh(part)
        poly = Poly3DCollection([[vertices[i] for i in face] for face in faces],
                                facecolors=[part['color']], linewidths=0.05, edgecolors=(0,0,0,0.12))
        axes.add_collection3d(poly)
    all_vertices = [vertex for part in parts for vertex in mesh(part)[0]]
    bounds = [(min(point[i] for point in all_vertices)-0.02,max(point[i] for point in all_vertices)+0.02) for i in range(3)]
    axes.set(xlim=bounds[0], ylim=bounds[1], zlim=(0,bounds[2][1]), xlabel='X / m (forward)', ylabel='Y / m (left)', zlabel='Z / m')
    axes.set_box_aspect((bounds[0][1]-bounds[0][0],bounds[1][1]-bounds[1][0],bounds[2][1]))
    axes.view_init(elev=24, azim=38)
    axes.set_title(f"EyeCar - visual model from measurements\nCamera width {d['camera_width']*1000:g} mm; plates {d['plate_length']*1000:g} x {d['plate_width']*1000:g} mm")
    figure.text(0.08,0.03,'Positions of electronics, wheelbase and some mounts are approximate. Not manufacturing CAD.',fontsize=9)
    figure.savefig(output/'eyecar preview.png',dpi=160,bbox_inches='tight')
    plt.close(figure)

    from matplotlib.patches import Polygon
    figure, axes = plt.subplots(2,2,figsize=(15,12),facecolor='white')
    for axis, projection, title in [(axes[0,0],(0,1),'Top / X-Y'),
                                     (axes[1,0],(0,2),'Side / X-Z'),
                                     (axes[0,1],(1,2),'Front / Y-Z')]:
        for part in parts:
            if '_tread_' in part['name']:
                continue
            vertices,_ = mesh(part)
            outline = convex_hull([(point[projection[0]]*1000,point[projection[1]]*1000) for point in vertices])
            axis.add_patch(Polygon(outline,closed=True,facecolor=(*part['color'][:3],0.13),
                                   edgecolor='#38434b',linewidth=0.45))
        axis.autoscale_view()
        axis.set_aspect('equal')
        axis.set_title(title)
        axis.set_xlabel('mm')
        axis.set_ylabel('mm')
        axis.grid(alpha=0.15)
        axis.margins(0.25)
    def dimension(axis,a,b,label):
        axis.annotate('',xy=a,xytext=b,arrowprops=dict(arrowstyle='<->',color='#075b91',lw=0.8))
        if abs(a[1]-b[1]) > abs(a[0]-b[0]):
            axis.text((a[0]+b[0])/2-4,(a[1]+b[1])/2,label,
                      color='#075b91',fontsize=9,rotation=90,ha='right',va='center')
        else:
            axis.text((a[0]+b[0])/2+3,(a[1]+b[1])/2+3,label,color='#075b91',fontsize=9)
    length,width = d['plate_length']*1000,d['plate_width']*1000
    bottom = d['chassis_bottom_z']*1000
    middle,upper = bottom+d['electronics_plate_offset']*1000,bottom+d['upper_plate_offset']*1000
    camera_width = d['camera_width']*1000
    camera_z = camera_center_z(d)*1000
    dimension(axes[0,0],(-length/2,width/2+45),(length/2,width/2+45),f'{length:g}')
    dimension(axes[0,0],(-length/2-20,-width/2),(-length/2-20,width/2),f'{width:g}')
    dimension(axes[0,0],(length/2+50,-d['bumper_width']*500),(length/2+50,d['bumper_width']*500),f"{d['bumper_width']*1000:g} bumper")
    dimension(axes[1,0],(-length/2-50,bottom),(-length/2-50,upper),f'{upper-bottom:g} chassis')
    dimension(axes[1,0],(-length/2-15,middle),(-length/2-15,upper),f'{upper-middle:g}')
    dimension(axes[1,0],(-length/2-15,bottom),(-length/2-15,middle),f'{middle-bottom:g}')
    dimension(axes[0,1],(-camera_width/2,camera_z+35),(camera_width/2,camera_z+35),f'{camera_width:g} camera')
    axes[1,1].axis('off')
    notes = [
        'EYECAR / MEASUREMENT REFERENCE', '',
        f'Two plates: {length:g} x {width:g} mm', f'Plate gaps: {upper-middle:g} + {middle-bottom:g} = {upper-bottom:g} mm',
        f"Wheels: radius {d['wheel_radius']*1000:g} mm", f"Front bumper: {d['bumper_length']*1000:g} x {d['bumper_width']*1000:g} mm; four IR modules below",
        f"Camera mast: {d['mast_height']*1000:g} high, {d['mast_width']*1000:g} wide", f"Mast: {d['mast_from_front']*1000:g} mm behind front plate edge",
        f"Camera bracket: {d['bracket_width']*1000:g} wide, {d['bracket_height']*1000:g} high", f"Camera bar: {camera_width:g} wide, {d['camera_height']*1000:g} high", '',
        f"PROVISIONAL: wheelbase {d['wheelbase']*1000:g}, track {d['wheel_track']*1000:g}, wheel width {d['wheel_width']*1000:g},",
        f"plate thickness {d['plate_thickness']*1000:g}, ground clearance, boards and mounts.", '',
        'Based on user photos/approximate measurements.',
        'Visual assembly, not a manufacturing drawing.',
        'All dimensions in mm. Verify geometry before fabrication.'
    ]
    axes[1,1].text(0.04,0.96,'\n'.join(notes),va='top',fontsize=11,linespacing=1.6)
    figure.suptitle('EyeCar - orthographic reference views',fontsize=18)
    figure.tight_layout(rect=(0,0,1,0.96))
    svg = output/'eyecar drawing.svg'
    figure.savefig(svg)
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n')
    figure.savefig(output/'eyecar drawing.png',dpi=150)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'models/eyecar/generated')
    parser.add_argument('--runtime-only', action='store_true')
    args = parser.parse_args()
    d = json.loads(DIMENSIONS.read_text())
    parts = parts_for(d)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    urdf = make_urdf(d,parts)
    (args.output_dir/'eyecar.urdf').write_text(urdf)
    parameters = 'robot_state_publisher:\n  ros__parameters:\n    robot_description: |\n'+''.join('      '+line+'\n' for line in urdf.splitlines())
    (args.output_dir/'robot_state_publisher.yaml').write_text(parameters)
    if not args.runtime_only:
        export_cad(args.output_dir,d,parts)
        preview(args.output_dir,d,parts)
    print(f'Generated EyeCar model in {args.output_dir}')


if __name__ == '__main__':
    main()
