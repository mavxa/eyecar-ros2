# EyeCar visual model

![EyeCar model](generated/eyecar%20preview.png)

Download the [URDF](generated/eyecar.urdf), [STL](generated/eyecar.stl),
[OpenSCAD source](generated/eyecar.scad), [DXF drawing](generated/eyecar%20drawing.dxf)
or [drawing preview](generated/eyecar%20drawing.png).

Edit `dimensions.json`, then restart RViz or run
`python scripts/eyecar_model.py` to regenerate the exports. The generator
uses boxes and cylinders, with fixed component links, steering joints and
continuous wheel joints. It is intended to be readable and editable.

User measurements used:

| Part | Size in mm |
| --- | --- |
| Two plates | 240 x 120 |
| Chassis stack | 105, split into 50 and 55 |
| Wheels | Radius 30 |
| Front bumper | 35 long x 160 wide |
| Camera mast | 160 high x 55 wide, 55 behind front plate edge |
| Camera holder | 85 wide x 40 high, width interpretation provisional |
| Long camera | 155 left-to-right x 25 high |

The stack is measured from a provisional drivetrain datum 15 mm above the
ground, so the upper plate is approximately 120 mm above ground. Camera mast
height is interpreted relative to that upper plate. This vertical interpretation
and the holder width can be adjusted independently when confirmed.

Wheelbase 170, wheel-center track 145, wheel width 23, plate thickness 3,
camera depth 25, electronics placement and all unmeasured mounts are estimates.
Four HC-SR04 modules use rear/right/left/front yaw 180/-90/+90/0 degrees.
Their centers share the electronics level at 80 mm above ground. The camera
is centered vertically in the holder, rather than sitting above it.
Four IR modules are shown beneath the front bumper. Firmware still reports
five IR channels; physical channel mapping is not inferred from the drawing.

`generated/` contains:

- `eyecar.urdf`: RViz/robot_state_publisher visual description, in meters.
- `robot_state_publisher.yaml`: generated ROS parameter file.
- `eyecar.scad`: editable OpenSCAD assembly, in millimeters.
- `eyecar.stl`: visual assembly mesh in millimeters, with overlapping components.
- `eyecar drawing.dxf`: R12 DXF orthographic reference for import into CAD software.
- `eyecar drawing.svg` and `.png`: readable orthographic reference views.
- `eyecar preview.png`: 3D preview.

The drawing and STL are not manufacturing-ready or a verified collision model.
KOMPAS was not found on the laptop, so no native `.cdw`/`.a3d` is produced.
DXF import into KOMPAS is an interchange route; it has not been verified here.

`rviz_bridge.py` receives telemetry through the existing read-only Pi bridge.
`eyecar_motion.py` integrates commands with a nominal bicycle model. Its pose,
wheel rotation and steering are predictions from commands, not sensor feedback.
Actual pose/speed need measured odometry. Nothing in this model changes Arduino
firmware or sends commands to the rover.

Two relevant Jazzy RViz limitations are handled in the generator/viewer:
[multiple visuals can share the first material](https://github.com/ros2/rviz/issues/1293)
and [small text has oversized word spacing](https://github.com/ros2/rviz/issues/1336).
Each visual part has its own fixed link; telemetry labels avoid spaces.
