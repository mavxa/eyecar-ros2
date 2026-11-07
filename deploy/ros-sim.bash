# Source in every simulation terminal, including RViz and student-node shells.
export ROS_DOMAIN_ID=42
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
unset CYCLONEDDS_URI ROS_LOCALHOST_ONLY ROS_STATIC_PEERS
