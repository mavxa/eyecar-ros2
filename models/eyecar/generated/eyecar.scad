// EyeCar visual reference; dimensions in mm. Not manufacturing geometry.
$fn=32;
// electronics_plate
color([0.08,0.09,0.1,1]) translate([0,0,65]) rotate([0,0,0]) cube([240.0,120.0,3.0], center=true);
// upper_plate
color([0.15,0.18,0.2,0.48]) translate([0,0,120]) rotate([0,0,0]) cube([240.0,120.0,3.0], center=true);
// post_-0.1_-0.045
color([0.67,0.7,0.73,1]) translate([-100,-45,92.5]) rotate([0,0,0]) cylinder(r=3.0,h=54.99999999999999,center=true);
// lower_post_-0.1_-0.045
color([0.67,0.7,0.73,1]) translate([-100,-45,40]) rotate([0,0,0]) cylinder(r=3.0,h=50.0,center=true);
// post_-0.1_0.045
color([0.67,0.7,0.73,1]) translate([-100,45,92.5]) rotate([0,0,0]) cylinder(r=3.0,h=54.99999999999999,center=true);
// lower_post_-0.1_0.045
color([0.67,0.7,0.73,1]) translate([-100,45,40]) rotate([0,0,0]) cylinder(r=3.0,h=50.0,center=true);
// post_0.1_-0.045
color([0.67,0.7,0.73,1]) translate([100,-45,92.5]) rotate([0,0,0]) cylinder(r=3.0,h=54.99999999999999,center=true);
// lower_post_0.1_-0.045
color([0.67,0.7,0.73,1]) translate([100,-45,40]) rotate([0,0,0]) cylinder(r=3.0,h=50.0,center=true);
// post_0.1_0.045
color([0.67,0.7,0.73,1]) translate([100,45,92.5]) rotate([0,0,0]) cylinder(r=3.0,h=54.99999999999999,center=true);
// lower_post_0.1_0.045
color([0.67,0.7,0.73,1]) translate([100,45,40]) rotate([0,0,0]) cylinder(r=3.0,h=50.0,center=true);
// lower_rail_-0.035
color([0.08,0.09,0.1,1]) translate([0,-35,20]) rotate([0,0,0]) cube([205.0,9.0,10.0], center=true);
// lower_rail_0.035
color([0.08,0.09,0.1,1]) translate([0,35,20]) rotate([0,0,0]) cube([205.0,9.0,10.0], center=true);
// transmission
color([0.08,0.09,0.1,1]) translate([-30,0,33]) rotate([0,0,0]) cube([75.0,45.0,25.0], center=true);
// motor
color([0.67,0.7,0.73,1]) translate([-45,35,37]) rotate([0,90,0]) cylinder(r=12.0,h=45.0,center=true);
// drive_shaft
color([0.67,0.7,0.73,1]) translate([0,0,35]) rotate([0,90,0]) cylinder(r=3.0,h=170.0,center=true);
// axle_-0.085
color([0.67,0.7,0.73,1]) translate([-85,0,30]) rotate([90,0,0]) cylinder(r=4.0,h=145.0,center=true);
// axle_0.085
color([0.67,0.7,0.73,1]) translate([85,0,30]) rotate([90,0,0]) cylinder(r=4.0,h=145.0,center=true);
// rear_left_wheel_tire
color([0.08,0.09,0.1,1]) translate([-85,72.5,30]) rotate([90,0,0]) cylinder(r=30.0,h=23.0,center=true);
// rear_left_wheel_rim
color([0.67,0.7,0.73,1]) translate([-85,72.5,30]) rotate([90,0,0]) cylinder(r=18.0,h=24.0,center=true);
// rear_left_wheel_hub
color([0.08,0.09,0.1,1]) translate([-85,72.5,30]) rotate([90,0,0]) cylinder(r=6.0,h=26.0,center=true);
// rear_left_wheel_tread_0
color([0.13,0.14,0.15,1]) translate([-85,72.5,59]) rotate([0,0,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_1
color([0.13,0.14,0.15,1]) translate([-73.90218,72.5,56.79251]) rotate([0,22.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_2
color([0.13,0.14,0.15,1]) translate([-64.4939,72.5,50.5061]) rotate([0,45,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_3
color([0.13,0.14,0.15,1]) translate([-58.20749,72.5,41.09782]) rotate([0,67.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_4
color([0.13,0.14,0.15,1]) translate([-56,72.5,30]) rotate([0,90,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_5
color([0.13,0.14,0.15,1]) translate([-58.20749,72.5,18.90218]) rotate([0,112.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_6
color([0.13,0.14,0.15,1]) translate([-64.4939,72.5,9.493903]) rotate([0,135,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_7
color([0.13,0.14,0.15,1]) translate([-73.90218,72.5,3.207494]) rotate([0,157.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_8
color([0.13,0.14,0.15,1]) translate([-85,72.5,1]) rotate([0,180,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_9
color([0.13,0.14,0.15,1]) translate([-96.09782,72.5,3.207494]) rotate([0,202.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_10
color([0.13,0.14,0.15,1]) translate([-105.5061,72.5,9.493903]) rotate([0,225,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_11
color([0.13,0.14,0.15,1]) translate([-111.7925,72.5,18.90218]) rotate([0,247.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_12
color([0.13,0.14,0.15,1]) translate([-114,72.5,30]) rotate([0,270,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_13
color([0.13,0.14,0.15,1]) translate([-111.7925,72.5,41.09782]) rotate([0,292.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_14
color([0.13,0.14,0.15,1]) translate([-105.5061,72.5,50.5061]) rotate([0,315,0]) cube([8.0,25.0,3.0], center=true);
// rear_left_wheel_tread_15
color([0.13,0.14,0.15,1]) translate([-96.09782,72.5,56.79251]) rotate([0,337.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tire
color([0.08,0.09,0.1,1]) translate([-85,-72.5,30]) rotate([90,0,0]) cylinder(r=30.0,h=23.0,center=true);
// rear_right_wheel_rim
color([0.67,0.7,0.73,1]) translate([-85,-72.5,30]) rotate([90,0,0]) cylinder(r=18.0,h=24.0,center=true);
// rear_right_wheel_hub
color([0.08,0.09,0.1,1]) translate([-85,-72.5,30]) rotate([90,0,0]) cylinder(r=6.0,h=26.0,center=true);
// rear_right_wheel_tread_0
color([0.13,0.14,0.15,1]) translate([-85,-72.5,59]) rotate([0,0,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_1
color([0.13,0.14,0.15,1]) translate([-73.90218,-72.5,56.79251]) rotate([0,22.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_2
color([0.13,0.14,0.15,1]) translate([-64.4939,-72.5,50.5061]) rotate([0,45,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_3
color([0.13,0.14,0.15,1]) translate([-58.20749,-72.5,41.09782]) rotate([0,67.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_4
color([0.13,0.14,0.15,1]) translate([-56,-72.5,30]) rotate([0,90,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_5
color([0.13,0.14,0.15,1]) translate([-58.20749,-72.5,18.90218]) rotate([0,112.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_6
color([0.13,0.14,0.15,1]) translate([-64.4939,-72.5,9.493903]) rotate([0,135,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_7
color([0.13,0.14,0.15,1]) translate([-73.90218,-72.5,3.207494]) rotate([0,157.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_8
color([0.13,0.14,0.15,1]) translate([-85,-72.5,1]) rotate([0,180,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_9
color([0.13,0.14,0.15,1]) translate([-96.09782,-72.5,3.207494]) rotate([0,202.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_10
color([0.13,0.14,0.15,1]) translate([-105.5061,-72.5,9.493903]) rotate([0,225,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_11
color([0.13,0.14,0.15,1]) translate([-111.7925,-72.5,18.90218]) rotate([0,247.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_12
color([0.13,0.14,0.15,1]) translate([-114,-72.5,30]) rotate([0,270,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_13
color([0.13,0.14,0.15,1]) translate([-111.7925,-72.5,41.09782]) rotate([0,292.5,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_14
color([0.13,0.14,0.15,1]) translate([-105.5061,-72.5,50.5061]) rotate([0,315,0]) cube([8.0,25.0,3.0], center=true);
// rear_right_wheel_tread_15
color([0.13,0.14,0.15,1]) translate([-96.09782,-72.5,56.79251]) rotate([0,337.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tire
color([0.08,0.09,0.1,1]) translate([85,72.5,30]) rotate([90,0,0]) cylinder(r=30.0,h=23.0,center=true);
// front_left_wheel_rim
color([0.67,0.7,0.73,1]) translate([85,72.5,30]) rotate([90,0,0]) cylinder(r=18.0,h=24.0,center=true);
// front_left_wheel_hub
color([0.08,0.09,0.1,1]) translate([85,72.5,30]) rotate([90,0,0]) cylinder(r=6.0,h=26.0,center=true);
// front_left_wheel_tread_0
color([0.13,0.14,0.15,1]) translate([85,72.5,59]) rotate([0,0,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_1
color([0.13,0.14,0.15,1]) translate([96.09782,72.5,56.79251]) rotate([0,22.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_2
color([0.13,0.14,0.15,1]) translate([105.5061,72.5,50.5061]) rotate([0,45,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_3
color([0.13,0.14,0.15,1]) translate([111.7925,72.5,41.09782]) rotate([0,67.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_4
color([0.13,0.14,0.15,1]) translate([114,72.5,30]) rotate([0,90,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_5
color([0.13,0.14,0.15,1]) translate([111.7925,72.5,18.90218]) rotate([0,112.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_6
color([0.13,0.14,0.15,1]) translate([105.5061,72.5,9.493903]) rotate([0,135,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_7
color([0.13,0.14,0.15,1]) translate([96.09782,72.5,3.207494]) rotate([0,157.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_8
color([0.13,0.14,0.15,1]) translate([85,72.5,1]) rotate([0,180,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_9
color([0.13,0.14,0.15,1]) translate([73.90218,72.5,3.207494]) rotate([0,202.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_10
color([0.13,0.14,0.15,1]) translate([64.4939,72.5,9.493903]) rotate([0,225,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_11
color([0.13,0.14,0.15,1]) translate([58.20749,72.5,18.90218]) rotate([0,247.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_12
color([0.13,0.14,0.15,1]) translate([56,72.5,30]) rotate([0,270,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_13
color([0.13,0.14,0.15,1]) translate([58.20749,72.5,41.09782]) rotate([0,292.5,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_14
color([0.13,0.14,0.15,1]) translate([64.4939,72.5,50.5061]) rotate([0,315,0]) cube([8.0,25.0,3.0], center=true);
// front_left_wheel_tread_15
color([0.13,0.14,0.15,1]) translate([73.90218,72.5,56.79251]) rotate([0,337.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tire
color([0.08,0.09,0.1,1]) translate([85,-72.5,30]) rotate([90,0,0]) cylinder(r=30.0,h=23.0,center=true);
// front_right_wheel_rim
color([0.67,0.7,0.73,1]) translate([85,-72.5,30]) rotate([90,0,0]) cylinder(r=18.0,h=24.0,center=true);
// front_right_wheel_hub
color([0.08,0.09,0.1,1]) translate([85,-72.5,30]) rotate([90,0,0]) cylinder(r=6.0,h=26.0,center=true);
// front_right_wheel_tread_0
color([0.13,0.14,0.15,1]) translate([85,-72.5,59]) rotate([0,0,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_1
color([0.13,0.14,0.15,1]) translate([96.09782,-72.5,56.79251]) rotate([0,22.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_2
color([0.13,0.14,0.15,1]) translate([105.5061,-72.5,50.5061]) rotate([0,45,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_3
color([0.13,0.14,0.15,1]) translate([111.7925,-72.5,41.09782]) rotate([0,67.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_4
color([0.13,0.14,0.15,1]) translate([114,-72.5,30]) rotate([0,90,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_5
color([0.13,0.14,0.15,1]) translate([111.7925,-72.5,18.90218]) rotate([0,112.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_6
color([0.13,0.14,0.15,1]) translate([105.5061,-72.5,9.493903]) rotate([0,135,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_7
color([0.13,0.14,0.15,1]) translate([96.09782,-72.5,3.207494]) rotate([0,157.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_8
color([0.13,0.14,0.15,1]) translate([85,-72.5,1]) rotate([0,180,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_9
color([0.13,0.14,0.15,1]) translate([73.90218,-72.5,3.207494]) rotate([0,202.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_10
color([0.13,0.14,0.15,1]) translate([64.4939,-72.5,9.493903]) rotate([0,225,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_11
color([0.13,0.14,0.15,1]) translate([58.20749,-72.5,18.90218]) rotate([0,247.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_12
color([0.13,0.14,0.15,1]) translate([56,-72.5,30]) rotate([0,270,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_13
color([0.13,0.14,0.15,1]) translate([58.20749,-72.5,41.09782]) rotate([0,292.5,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_14
color([0.13,0.14,0.15,1]) translate([64.4939,-72.5,50.5061]) rotate([0,315,0]) cube([8.0,25.0,3.0], center=true);
// front_right_wheel_tread_15
color([0.13,0.14,0.15,1]) translate([73.90218,-72.5,56.79251]) rotate([0,337.5,0]) cube([8.0,25.0,3.0], center=true);
// raspberry_pi
color([0.08,0.42,0.22,1]) translate([-57,0,73]) rotate([0,0,0]) cube([85.0,56.0,3.0], center=true);
// pi_usb_-0.018
color([0.67,0.7,0.73,1]) translate([-20,-18,82]) rotate([0,0,0]) cube([16.0,15.0,14.0], center=true);
// pi_usb_0.018
color([0.67,0.7,0.73,1]) translate([-20,18,82]) rotate([0,0,0]) cube([16.0,15.0,14.0], center=true);
// pi_chip
color([0.08,0.09,0.1,1]) translate([-60,0,77]) rotate([0,0,0]) cube([16.0,16.0,4.0], center=true);
// arduino_mega
color([0.04,0.29,0.57,1]) translate([50,0,73]) rotate([0,0,0]) cube([102.0,54.0,3.0], center=true);
// expansion_shield
color([0.15,0.2,0.24,1]) translate([50,0,84]) rotate([0,0,0]) cube([90.0,53.0,3.0], center=true);
// headers_-0.023
color([0.08,0.09,0.1,1]) translate([50,-23,89]) rotate([0,0,0]) cube([85.0,5.0,8.0], center=true);
// headers_0.023
color([0.08,0.09,0.1,1]) translate([50,23,89]) rotate([0,0,0]) cube([85.0,5.0,8.0], center=true);
// front_bumper
color([0.08,0.09,0.1,1]) translate([137.5,0,18]) rotate([0,0,0]) cube([35.0,160.0,6.0], center=true);
// ir_0_board
color([0.04,0.29,0.57,1]) translate([135.5,-45,12]) rotate([0,0,0]) cube([18.0,10.0,2.0], center=true);
// ir_0_receiver
color([0.08,0.09,0.1,1]) translate([140.5,-45,9]) rotate([0,0,0]) cube([6.0,6.0,4.0], center=true);
// ir_1_board
color([0.04,0.29,0.57,1]) translate([135.5,-15,12]) rotate([0,0,0]) cube([18.0,10.0,2.0], center=true);
// ir_1_receiver
color([0.08,0.09,0.1,1]) translate([140.5,-15,9]) rotate([0,0,0]) cube([6.0,6.0,4.0], center=true);
// ir_2_board
color([0.04,0.29,0.57,1]) translate([135.5,15,12]) rotate([0,0,0]) cube([18.0,10.0,2.0], center=true);
// ir_2_receiver
color([0.08,0.09,0.1,1]) translate([140.5,15,9]) rotate([0,0,0]) cube([6.0,6.0,4.0], center=true);
// ir_3_board
color([0.04,0.29,0.57,1]) translate([135.5,45,12]) rotate([0,0,0]) cube([18.0,10.0,2.0], center=true);
// ir_3_receiver
color([0.08,0.09,0.1,1]) translate([140.5,45,9]) rotate([0,0,0]) cube([6.0,6.0,4.0], center=true);
// us_rear_bracket
color([0.08,0.09,0.1,1]) translate([-117,-3.67394e-16,69]) rotate([0,0,180]) cube([8.0,40.0,10.0], center=true);
// us_rear_pcb
color([0.04,0.29,0.57,1]) translate([-120,0,80]) rotate([0,0,180]) cube([2.0,45.0,20.0], center=true);
// us_rear_0
color([0.67,0.7,0.73,1]) translate([-127,12,80]) rotate([0,90,180]) cylinder(r=8.0,h=12.0,center=true);
// us_rear_1
color([0.67,0.7,0.73,1]) translate([-127,-12,80]) rotate([0,90,180]) cylinder(r=8.0,h=12.0,center=true);
// us_right_bracket
color([0.08,0.09,0.1,1]) translate([80,-42,69]) rotate([0,0,-90]) cube([8.0,40.0,10.0], center=true);
// us_right_pcb
color([0.04,0.29,0.57,1]) translate([80,-45,80]) rotate([0,0,-90]) cube([2.0,45.0,20.0], center=true);
// us_right_0
color([0.67,0.7,0.73,1]) translate([68,-52,80]) rotate([0,90,-90]) cylinder(r=8.0,h=12.0,center=true);
// us_right_1
color([0.67,0.7,0.73,1]) translate([92,-52,80]) rotate([0,90,-90]) cylinder(r=8.0,h=12.0,center=true);
// us_left_bracket
color([0.08,0.09,0.1,1]) translate([80,42,69]) rotate([0,0,90]) cube([8.0,40.0,10.0], center=true);
// us_left_pcb
color([0.04,0.29,0.57,1]) translate([80,45,80]) rotate([0,0,90]) cube([2.0,45.0,20.0], center=true);
// us_left_0
color([0.67,0.7,0.73,1]) translate([92,52,80]) rotate([0,90,90]) cylinder(r=8.0,h=12.0,center=true);
// us_left_1
color([0.67,0.7,0.73,1]) translate([68,52,80]) rotate([0,90,90]) cylinder(r=8.0,h=12.0,center=true);
// us_front_bracket
color([0.08,0.09,0.1,1]) translate([112,0,69]) rotate([0,0,0]) cube([8.0,40.0,10.0], center=true);
// us_front_pcb
color([0.04,0.29,0.57,1]) translate([115,0,80]) rotate([0,0,0]) cube([2.0,45.0,20.0], center=true);
// us_front_0
color([0.67,0.7,0.73,1]) translate([122,-12,80]) rotate([0,90,0]) cylinder(r=8.0,h=12.0,center=true);
// us_front_1
color([0.67,0.7,0.73,1]) translate([122,12,80]) rotate([0,90,0]) cylinder(r=8.0,h=12.0,center=true);
// camera_mast
color([0.08,0.09,0.1,1]) translate([65,0,200]) rotate([0,0,0]) cube([4.0,55.0,160.0], center=true);
// mast_foot
color([0.08,0.09,0.1,1]) translate([65,0,124]) rotate([0,0,0]) cube([25.0,65.0,6.0], center=true);
// camera_holder_-0.0425
color([0.08,0.09,0.1,1]) translate([65,-42.5,300]) rotate([0,0,0]) cube([20.0,4.0,40.0], center=true);
// camera_holder_0.0425
color([0.08,0.09,0.1,1]) translate([65,42.5,300]) rotate([0,0,0]) cube([20.0,4.0,40.0], center=true);
// camera_holder_bar
color([0.08,0.09,0.1,1]) translate([65,0,283]) rotate([0,0,0]) cube([25.0,85.0,6.0], center=true);
// camera_bar
color([0.12,0.14,0.16,1]) translate([75,0,300]) rotate([0,0,0]) cube([25.0,155.0,25.0], center=true);
// camera_lens_ring
color([0.67,0.7,0.73,1]) translate([87.5,0,300]) rotate([0,90,0]) cylinder(r=10.0,h=6.0,center=true);
// camera_lens
color([0.02,0.08,0.12,1]) translate([92.5,0,300]) rotate([0,90,0]) cylinder(r=7.0,h=4.0,center=true);
