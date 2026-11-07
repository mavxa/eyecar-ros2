# Source on the laptop; the Pi uses the separate deploy/dds/rover.xml profile.
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/dds/laptop.xml"
unset ROS_LOCALHOST_ONLY ROS_STATIC_PEERS
