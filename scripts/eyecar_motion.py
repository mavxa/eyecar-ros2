"""Nominal bicycle motion from EyeCar commands, not measured odometry."""

import math


class CommandEstimate:
    def __init__(self, dimensions):
        self.dimensions = dimensions
        self.reset()

    def reset(self):
        self.x = self.y = self.yaw = self.wheel_angle = 0.0
        self.speed = self.steering = self.yaw_rate = 0.0
        self.command = (0.0, 0.0)
        self.received_at = None
        self.updated_at = None

    def set_command(self, speed, steering_command, now):
        self.command = (speed, steering_command)
        self.received_at = now

    def step(self, now):
        dt = min(max(now-self.updated_at, 0.0), 0.1) if self.updated_at is not None else 0.0
        self.updated_at = now
        fresh = self.received_at is not None and 0 <= now-self.received_at < self.dimensions['command_timeout_s']
        speed, steering_command = self.command if fresh else (0.0, 0.0)
        steering = max(-1.0, min(1.0, steering_command/self.dimensions['angular_command_limit']))
        self.speed = speed
        self.steering = steering*math.radians(self.dimensions['estimated_max_steering_deg'])
        # EyeCar angular.z is used by the base driver as a steering command.
        # It is not a measured yaw rate, so use an explicitly approximate bicycle model.
        self.yaw_rate = speed*math.tan(self.steering)/self.dimensions['wheelbase']
        middle_yaw = self.yaw+self.yaw_rate*dt/2
        self.x += speed*math.cos(middle_yaw)*dt
        self.y += speed*math.sin(middle_yaw)*dt
        self.yaw = math.atan2(math.sin(self.yaw+self.yaw_rate*dt), math.cos(self.yaw+self.yaw_rate*dt))
        self.wheel_angle = (self.wheel_angle+speed/self.dimensions['wheel_radius']*dt) % math.tau
        return fresh

    def steering_angles(self):
        if abs(self.steering) < 1e-8:
            return 0.0, 0.0
        radius = self.dimensions['wheelbase']/math.tan(self.steering)
        half_track = self.dimensions['wheel_track']/2
        return tuple(math.atan(self.dimensions['wheelbase']/(radius-side))
                     for side in (half_track, -half_track))
