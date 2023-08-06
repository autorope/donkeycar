import time
import math

debug = False

try:
    from pymavlink import mavutil
except ImportError:
    print("Pymavlink not found.  Please install: pip install pymavlink")


class MavlinkIMUPart:
    def __init__(self, connection_string):
        # Create the connection to Pixhawk
        self.master = mavutil.mavlink_connection(connection_string, baud=115200)
        self.master.wait_heartbeat()
        print("Heartbeat from system (system %u component %u)" % (self.master.target_system, self.master.target_component))
        
        # IMU data
        self.roll = 0
        self.pitch = 0
        self.yaw = 0

        # Position data
        self.lat = 0.0
        self.lon = 0.0
        self.alt = 0.0

        # Velocity data
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0

        # Flag to control the data reading thread
        self.running = True


    def update(self):
        while self.running:
            self.poll()

    def poll(self):
       message = self.master.recv_match()
       if message is not None:
           attitude_msg = self.master.recv_match(type='ATTITUDE', blocking=True)
           position_msg = self.master.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
           velocity_msg = self.master.recv_match(type='VFR_HUD', blocking=True)

            # Updating IMU data
           self.roll = attitude_msg.roll
           self.pitch = attitude_msg.pitch
           self.yaw = attitude_msg.yaw
                
           # Updating Position data
           self.lat = position_msg.lat / 1e7  # Convert to degrees
           self.lon = position_msg.lon / 1e7  # Convert to degrees
           self.alt = position_msg.alt / 1e3  # Convert to meters

           # Updating Velocity data (VFR_HUD provides ground speeds)
           self.vx = velocity_msg.groundspeed * math.cos(self.yaw)
           self.vy = velocity_msg.groundspeed * math.sin(self.yaw)
           self.vz = velocity_msg.climb
       else:
           print("no Mavlink data")

    def run_threaded(self):
        return (self.roll, self.pitch, self.yaw, 
                self.lat, self.lon, self.alt,
                self.vx, self.vy, self.vz)

    def shutdown(self):
        self.master.close()
        self.running = False
