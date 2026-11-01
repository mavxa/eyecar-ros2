#!/usr/bin/env python3
"""Export the shared EyeCar geometry as a physical Webots robot."""
import argparse
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from eyecar_model import DIMENSIONS, ROOT, camera_center_z, make_urdf, parts_for, vector

PACKAGE = ROOT / 'ros2_ws/src/eyecar_sim'


def axis_angle(rpy):
    r, p, y = (v / 2 for v in rpy)
    c, s = math.cos, math.sin
    q = (s(r)*c(p)*c(y)-c(r)*s(p)*s(y),
         c(r)*s(p)*c(y)+s(r)*c(p)*s(y),
         c(r)*c(p)*s(y)-s(r)*s(p)*c(y))
    norm = math.sqrt(sum(v*v for v in q))
    w = c(r)*c(p)*c(y)+s(r)*s(p)*s(y)
    return vector((*[v/norm for v in q], 2*math.atan2(norm, w))) if norm > 1e-10 else '0 0 1 0'


def shape(part, origin=(0, 0, 0)):
    xyz = vector([a-b for a, b in zip(part['center'], origin)])
    if part['kind'] == 'box':
        geometry = f'Box {{ size {vector(part["size"])} }}'
    else:
        radius, length = part['size']
        geometry = f'Cylinder {{ radius {radius} height {length} subdivision 16 }}'
    return f'''Pose {{ translation {xyz} rotation {axis_angle(part['rpy'])}
      children [ Shape {{ appearance PBRAppearance {{ baseColor {vector(part['color'][:3])}
        roughness 0.8 metalness 0 }} geometry {geometry} }} ] }}'''


def robot_proto(d):
    parts = parts_for(d)
    children = [shape(p) for p in parts if p['link'] == 'base_link']
    for end, x in [('rear', -d['wheelbase']/2), ('front', d['wheelbase']/2)]:
        for side, sign in [('left', 1), ('right', -1)]:
            name = f'{end}_{side}'
            center = (x, sign*d['wheel_track']/2, d['wheel_radius'])
            visual = '\n'.join(shape(p, center) for p in parts if p['link'] == name+'_wheel')
            anchor = '0 0 0' if end == 'front' else vector(center)
            wheel = f'''HingeJoint {{
              jointParameters HingeJointParameters {{ axis 0 1 0 anchor {anchor} dampingConstant 0.001 }}
              device [ RotationalMotor {{ name "{name}_motor" maxVelocity 25 maxTorque 0.15 }}
                       PositionSensor {{ name "{name}_encoder" }} ]
              endPoint Solid {{ translation {anchor} name "{name}_wheel"
                children [ {visual} ] contactMaterial "eyecar_tire"
                boundingObject Pose {{ rotation 1 0 0 1.570796327
                  children [ Cylinder {{ radius {d['wheel_radius']} height {d['wheel_width']} }} ] }}
                physics Physics {{ density -1 mass 0.05 }} }} }}'''
            if end == 'front':
                wheel = f'''HingeJoint {{
                  jointParameters HingeJointParameters {{ axis 0 0 1 anchor {vector(center)} }}
                  device [ RotationalMotor {{ name "{name}_steer" minPosition -0.8 maxPosition 0.8
                    maxVelocity 4 maxTorque 0.5 }} PositionSensor {{ name "{name}_steer_encoder" }} ]
                  endPoint Solid {{ translation {vector(center)} name "{name}_knuckle"
                    children [ {wheel} ] boundingObject Sphere {{ radius 0.004 }}
                    physics Physics {{ density -1 mass 0.01 }} }} }}'''
            children.append(wheel)
    for sensor in d['sensors']:
        children.append(f'''DistanceSensor {{ name "us_{sensor['name']}"
          translation {vector([sensor[k] for k in ('x', 'y', 'z')])}
          rotation 0 0 1 {math.radians(sensor['yaw_deg'])} type "sonar"
          numberOfRays 5 aperture 0.26 lookupTable [ 0 0 0, 4 4 0 ] }}''')
    for i in range(5):
        children.append(f'''DistanceSensor {{ name "ir_{i}"
          translation {d['plate_length']/2+0.01} {(i-2)*0.022} 0.009
          rotation 0 1 0 1.570796327 type "infra-red"
          lookupTable [ 0 1023 0, 0.06 0 0 ] }}''')
    for i in range(13):
        children.append(f'''LED {{ name "led_{i}" translation {-0.06+i*0.01} 0.064 0.12
          gradual TRUE color [] children [ Shape {{
            appearance Appearance {{ material Material {{ diffuseColor 0 0 0 emissiveColor 0 0 0 }} }}
            geometry Box {{ size 0.007 0.004 0.007 }} }} ] }}''')
    camera_x = d['plate_length']/2-d['mast_from_front']+0.015+d['camera_depth']/2
    children.append(f'''Camera {{ name "camera" translation {camera_x} 0 {camera_center_z(d)}
      width 320 height 240 fieldOfView 1.05 near 0.01 far 10 }}''')
    children.extend(['GPS { name "gps" }', 'InertialUnit { name "imu" }'])
    collision = [f'''Pose {{ translation 0 0 0.072 children [
      Box {{ size {d['plate_length']} {d['plate_width']} 0.10 }} ] }}''']
    for part in parts:
        if part['name'] in ('camera_mast', 'camera_bar', 'front_bumper'):
            collision.append(f'''Pose {{ translation {vector(part['center'])}
              children [ Box {{ size {vector(part['size'])} }} ] }}''')
    return '''#VRML_SIM R2025a utf8
# Generated from models/eyecar/dimensions.json. Physics values are provisional.
PROTO EyeCar [
  field SFVec3f translation 0 0 0.003
  field SFRotation rotation 0 0 1 0
]
{
  Robot {
    translation IS translation rotation IS rotation
    name "eyecar" controller "<extern>"
    children [
''' + '\n'.join(children) + '''
    ]
    boundingObject Group { children [
''' + '\n'.join(collision) + '''
    ] }
    physics Physics { density -1 mass 1.0 centerOfMass [ 0 0 0.06 ] }
  }
}
'''


def outputs(d):
    urdf = ET.fromstring(make_urdf(d, parts_for(d)))
    webots = ET.SubElement(urdf, 'webots')
    ET.SubElement(webots, 'plugin', type='eyecar_sim.driver.EyeCarDriver')
    names = ['camera', 'gps', 'imu'] + [f'us_{s["name"]}' for s in d['sensors']]
    names += [f'ir_{i}' for i in range(5)] + [f'led_{i}' for i in range(13)]
    for name in names:
        device = ET.SubElement(webots, 'device', reference=name)
        ET.SubElement(ET.SubElement(device, 'ros'), 'enabled').text = 'false'
    ET.indent(urdf)
    return {'protos/EyeCar.proto': robot_proto(d),
            'config/eyecar.urdf': ET.tostring(urdf, encoding='unicode')+'\n',
            'config/dimensions.json': json.dumps(d, indent=2)+'\n'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name, data in outputs(json.loads(DIMENSIONS.read_text())).items():
        path = PACKAGE / name
        if args.check:
            if not path.exists() or path.read_text() != data:
                raise SystemExit(f'Stale Webots asset: {name}; run python3 scripts/eyecar_webots.py')
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
    print('Webots geometry is current.' if args.check else 'Generated EyeCar Webots assets.')


if __name__ == '__main__':
    main()
