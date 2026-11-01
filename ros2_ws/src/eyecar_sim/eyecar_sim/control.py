"""Nominal Ackermann mapping; not an identified model of the real motor/ESC."""
import math


WHEELS = ('rear_left', 'rear_right', 'front_left', 'front_right')


def wheel_commands(linear, angular, d):
    if not math.isfinite(linear) or not math.isfinite(angular):
        linear = angular = 0.0
    speed = max(-0.25, min(0.25, linear))
    steering = max(-1.0, min(1.0, angular/d['angular_command_limit']))
    curvature = math.tan(steering*math.radians(d['estimated_max_steering_deg']))/d['wheelbase']
    left, right = (1-curvature*d['wheel_track']/2, 1+curvature*d['wheel_track']/2)
    angles = [math.atan2(d['wheelbase']*curvature, side) for side in (left, right)]
    speeds = [speed*side/d['wheel_radius'] for side in
              (left, right, math.hypot(left, curvature*d['wheelbase']),
               math.hypot(right, curvature*d['wheelbase']))]
    return speeds, angles


def ultrasonic_cm(distance):
    if not math.isfinite(distance) or distance >= 4.0:
        return 0
    return max(1, min(400, round(distance*100)))
