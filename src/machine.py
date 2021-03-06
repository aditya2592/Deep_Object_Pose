#!/usr/bin/env python

# Copyright (c) 2018 NVIDIA Corporation. All rights reserved.
# This work is licensed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode

"""
This file starts a ROS node to run DOPE,
listening to an image topic and publishing poses.
"""

from __future__ import print_function
import yaml
import sys
import numpy as np
import cv2
import tf
import math
import rospy
import rospkg

import rosparam
from geometry_msgs.msg import PoseStamped, Pose
from time import sleep
from sensor_msgs.msg import JointState

import roslaunch
# Import DOPE code
rospack = rospkg.RosPack()
g_path2package = rospack.get_path('dope')
# planner_path = rospack.get_path('cruzr_planner')
planner_path = rospack.get_path('walker_planner')


def start_octomap_server():
    # package = 'cruzr_planner'
    # executable = '.launch'
    # node = roslaunch.core.Node(package, executable)
    #
    launch = roslaunch.scriptapi.ROSLaunch()
    # launch.start()

    # process = launch.launch(node)

    uuid = roslaunch.rlutil.get_or_generate_uuid(None, False)
    roslaunch.configure_logging(uuid)
    launch = roslaunch.parent.ROSLaunchParent(uuid, [planner_path+"/launch/load_pointcloud.launch"])
    launch.start()
    rospy.loginfo("started")

def wait_till_done_and_publish(param, done_msg, rate, pub, msg):

    while not rospy.is_shutdown():
        try:
            pub.publish(msg)
            if (rospy.get_param(param) == 1):
                rospy.logwarn (done_msg)
                break
            rate.sleep()
        except KeyboardInterrupt:
            print('interrupted!')

def wait_till_done(param, done_msg, rate):

    while not rospy.is_shutdown():
        try:
            if (rospy.get_param(param) == 1):
                rospy.logwarn (done_msg)
                break
            rate.sleep()
        except KeyboardInterrupt:
            print('interrupted!')


# object_pose = None
transformed_object_pose = None
def perch_callback(data):
    from geometry_msgs.msg import Quaternion
    from tf.transformations import quaternion_from_euler, quaternion_multiply

    global transformed_object_pose

    object_pose = data.pose
    print("Detected Pose : {}".format(object_pose))
    q_orig = [0,0,0,0]
    q_orig[0] = object_pose.orientation.x
    q_orig[1] = object_pose.orientation.y
    q_orig[2] = object_pose.orientation.z
    q_orig[3] = object_pose.orientation.w
    print(q_orig)
    # q_orig = Quaternion(q_orig[0], q_orig[1], q_orig[2], q_orig[3])
    # q_rot_1 = quaternion_from_euler(0, 0, -math.pi/2)
    q_rot_1 = quaternion_from_euler(0, 0, 0)
    q_new = quaternion_multiply(q_rot_1, q_orig)
    # q_rot_2 = quaternion_from_euler(0,math.pi/2, 0)
    # q_new = quaternion_multiply(q_rot_2, q_new)

    print(q_new)

    pose = PoseStamped()
    pose.header.stamp = rospy.Time.now()
    pose.header.frame_id = data.header.frame_id
    pose.pose.position.x = object_pose.position.x
    pose.pose.position.y = object_pose.position.y
    pose.pose.position.z = object_pose.position.z + 0.05

    pose.pose.orientation.x = q_new[0]
    pose.pose.orientation.y = q_new[1]
    pose.pose.orientation.z = q_new[2]
    pose.pose.orientation.w = q_new[3]
    transformed_object_pose = pose


    return

def wait_till_done_perch(object_name, param, done_msg, rate):
    from std_msgs.msg import String

    pub = rospy.Publisher('/requested_object', String, queue_size=10)
    publish_once = 0

    rospy.Subscriber("/perch_pose", PoseStamped, perch_callback)
    while not rospy.is_shutdown():
        try:
            if (rospy.get_param(param) == 1):
                rospy.logwarn (done_msg)
                break
            if publish_once < 10:
                pub.publish(String(object_name))
                publish_once += 1
            rate.sleep()
        except KeyboardInterrupt:
            print('interrupted!')

def wait_till_done_perch_grasp(param, done_msg, rate):
    dope_pose = rospy.Publisher('/dope/pose_world_object', PoseStamped, queue_size=10)
    print("Publishing transformed pose until grasp")
    print(transformed_object_pose)
    while not rospy.is_shutdown():
        try:
            if (rospy.get_param(param) == 1):
                rospy.logwarn (done_msg)
                break
            else:
                dope_pose.publish(transformed_object_pose)
            rate.sleep()
        except KeyboardInterrupt:
            print('interrupted!')

def wait_till_done_perch_planner(param, done_msg, rate):
    dope_pose = rospy.Publisher('/Grasps', PoseStamped, queue_size=10)
    print("Publishing transformed pose until grasp")
    print(transformed_object_pose)
    while not rospy.is_shutdown():
        try:
            if (rospy.get_param(param) == 1):
                rospy.logwarn (done_msg)
                break
            else:
                dope_pose.publish(transformed_object_pose)
            rate.sleep()
        except KeyboardInterrupt:
            print('interrupted!')

def setup_variables():
    rospy.set_param("object_recognition_request", 0)
    rospy.set_param("object_recognition_done", 0)
    rospy.set_param("perch_done", 0)
    rospy.set_param("table_segmentation_request", 0)
    rospy.set_param("table_segmentation_done", 0)
    rospy.set_param("grasp_request", 0)
    rospy.set_param("grasp_done", 0)
    rospy.set_param("walker_planner_request", 0)
    rospy.set_param("walker_planner_done", 0)
    rospy.set_param("controller_request", 0)
    rospy.set_param("controller_done", 0)
    rospy.set_param("trac_ik_request", 0)
    rospy.set_param("trac_ik_done", 0)
    rospy.set_param("lift_request", 0)
    rospy.set_param("skip_states", 1)
    # rospy.set_param("hand_open_request", 1)

def load_yaml(yaml_path, ros_param_name):

    # with open(yaml_path, 'r') as stream:
    #     try:
    #         rospy.logwarn("Loading Planner Home state parameters from '{}'...".format(yaml_path))
    #         params = yaml.load(stream)
    #         rospy.set_param(ros_param_name, params['initial_configuration']['joint_state'])
    #     except yaml.YAMLError as exc:
    #         rospy.logerr(exc)
    paramlist=rosparam.load_file(yaml_path)
    for params, ns in paramlist:
        rosparam.upload_params(ns,params)


def get_transform_pose(source, target, pose):
    msg = PoseStamped()
    msg.header.frame_id = source
    msg.header.stamp = rospy.Time(0)
    msg.pose = pose
    tf_listener = tf.TransformListener()
    now = rospy.Time.now()
    rospy.logwarn("Waiting for transform")
    rate = rospy.Rate(10.0)
    while not rospy.is_shutdown():
        try:
            translation, rotation = tf_listener.lookupTransform(target, source, rospy.Time(0))
            out_msg = tf_listener.transformPose(target, msg)
            rospy.logwarn("Transformed pose found")
            return out_msg.pose
        except (tf.LookupException, tf.ConnectivityException, tf.ExtrapolationException):
            continue
        rate.sleep()



def go_to_custom_goal(pose, rate, mode, controller=True):
    grasp_publisher = rospy.Publisher(
        '/Grasps',
        PoseStamped,
        queue_size=10
    )
    msg = PoseStamped()
    msg.header.frame_id = "map"
    msg.header.stamp = rospy.Time.now()
    msg.pose = pose
    rospy.logwarn ("Requesting Initial Planner")
    rospy.set_param("walker_planner_mode", mode)
    rospy.set_param("walker_planner_request", 1)

    wait_till_done_and_publish("walker_planner_done", "Done Init Planner", rate, grasp_publisher, msg)
    rospy.set_param("walker_planner_done", 0)

    if controller:
        rospy.logwarn ("Requesting Init Controller")
        rospy.set_param("controller_request", 1)
        rospy.set_param("skip_states", 1)
        wait_till_done("controller_done", "Done Init Controller", rate)
        rospy.set_param("controller_done", 0)
    else:
        sleep(10)

def joint_state_callback(data):
    # rospy.loginfo(rospy.get_caller_id() + "I heard %s", data.position)
    joint_position_list = [{'name': 'x', 'position': 0.0}, {'name': 'y', 'position': 0.0}, {'name': 'theta', 'position': 0.0}]
    for name, position in zip(data.name, data.position):
        joint_position_list.append({
            'name' : name,
            'position' : position
        })
    # print(joint_position_list)
    rospy.set_param('initial_configuration/joint_state', joint_position_list)

if __name__ == "__main__":
    '''Main routine to run DOPE'''


    try:
        rospy.init_node('cruiser_state_machine', anonymous=True, log_level=rospy.INFO)
        rate = rospy.Rate(5)
        setup_variables()
        # sleep(10)

        myargv = rospy.myargv(argv=sys.argv)
        print(myargv)

        # start_octomap_server()

        if '--object_only' not in myargv:
            pose = Pose()
            if '--target' in myargv:
                # Table location
                print("Moving to table location")

                # Hector Slam
                pose.position.x, pose.position.y, pose.position.z = (-0.0293, -0.0013, 1.06)
                pose.orientation.x = 0
                pose.orientation.y = 0
                pose.orientation.z, pose.orientation.w = (0.00, 1)
                # pose.orientation.z, pose.orientation.w = (0.0703, 0.9975)

            elif '--initial' in myargv:
                # Hector Slam
                pose.position.x, pose.position.y, pose.position.z = (0.0, 0.0, 1.06)
                pose.orientation.x = 0
                pose.orientation.y = 0
                pose.orientation.z, pose.orientation.w = (0.0, 1)

            else:
                # Table location
                print("ERROR : --target or --initial not specified")
                sys.exit()
            config_name = "walker_goal.yaml"
            yaml_path = '{}/experiments/{}'.format(planner_path, config_name)
            load_yaml(yaml_path, "initial_configuration/joint_state")
            go_to_custom_goal(pose, rate, "BASE")

        if '--base_only' not in myargv:

            # sleep(30)
            # gain - 0.4 - angular, same for last state angular, max - 0.4
            rospy.set_param("hand_open_request", 1)
            # start_octomap_server()

            if '--custom_home_state' in myargv:
                # Use the planner to go to a custom home location
                rospy.logwarn ("Requesting Hand to Custom Home State")

                # First read the goal state which is at hand by the side
                config_name = "walker_goal.yaml"
                yaml_path = '{}/experiments/{}'.format(planner_path, config_name)

                pose = Pose()
                # pose.position.x, pose.position.y, pose.position.z = (0.304, -0.507, 0.795)
                pose.position.x, pose.position.y, pose.position.z = (0.40, -0.18, 0.785)
                pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w \
                    = (0.282, 0.155, 0.702, 0.635)
                pose_in_map = get_transform_pose('base_footprint', 'map', pose)
                load_yaml(yaml_path, "initial_configuration/joint_state")

                go_to_custom_goal(pose_in_map, rate, "FULLBODY", controller=True)
            else:

                if '--use_perch' not in myargv:
                    rospy.logwarn ("Requesting Object")
                    rospy.set_param("object_recognition_request", 1)
                    wait_till_done("object_recognition_done", "Done Object", rate)
                else:
                    rospy.logwarn ("Requesting PERCH Object")
                    wait_till_done_perch("004_sugar_box", "perch_done", "Done Perch", rate)


                if '--include_table_pose' in myargv:
                    rospy.logwarn ("Requesting Table Segmentation")
                    rospy.set_param("table_segmentation_request", 1)
                    wait_till_done("table_segmentation_done", "Done Table Segmentation", rate)

                rospy.logwarn ("Requesting Grasp")
                rospy.set_param("grasp_request", 1)
                if '--use_perch' not in myargv:
                    wait_till_done("grasp_done", "Done Grasp", rate)
                # else:
                #     wait_till_done_perch_grasp("grasp_done", "Done Grasp", rate)

                if '--custom_home_state' in myargv:
                    # If custom home state was used the new goal state would be in this file
                    config_name = "walker_goal_custom_home.yaml"
                    yaml_path = '{}/experiments/{}'.format(planner_path, config_name)
                    load_yaml(yaml_path, "initial_configuration/joint_state")
                else:
                    # Read original goal state for hand by the side
                    config_name = "walker_goal.yaml"
                    yaml_path = '{}/experiments/{}'.format(planner_path, config_name)
                    load_yaml(yaml_path, "initial_configuration/joint_state")

                rospy.logwarn ("Requesting Planner")
                rospy.set_param("walker_planner_mode", "FULLBODY")
                rospy.set_param("walker_planner_request", 1)
                if '--use_perch' not in myargv:
                    wait_till_done("walker_planner_done", "Done Planner", rate)
                else:
                    wait_till_done_perch_planner("walker_planner_done", "Done Planner", rate)

                rospy.set_param("walker_planner_done", 0)

                rospy.logwarn ("Requesting Controller")
                rospy.set_param("skip_states", 1)
                rospy.set_param("controller_request", 1)
                wait_till_done("controller_done", "Done Controller", rate)
                rospy.set_param("controller_done", 0)

                if '--use_perch' in myargv:
                    rospy.logwarn ("Requesting Hand Close")
                    rospy.set_param("hand_close_request", 1)

                    # rospy.logwarn ("Requesting Trac IK")
                    # rospy.set_param("lift_request", 1)
                    # sleep(2)
                    # # go_to_custom_goal(pose_in_map, rate, "FULLBODY", controller=True)
                    # rospy.set_param("trac_ik_request", 1)
                    # wait_till_done("trac_ik_done", "Done Trac IK", rate)
                    #
                    # rospy.logwarn ("Requesting Controller")
                    # rospy.set_param("skip_states", 0)
                    # rospy.set_param("controller_request", 1)
                    # wait_till_done("controller_done", "Done Controller", rate)
                    # rospy.set_param("controller_done", 0)
                    # rospy.set_param("trac_ik_done", 0)

                if '--incl_trac_ik' in myargv:
                    # Rerun grasping in case base moved
                    # rospy.logwarn ("Requesting Object Again")
                    # rospy.set_param("object_recognition_request", 1)
                    # wait_till_done("object_recognition_done", "Done Object", rate)
                    #
                    # rospy.logwarn ("Requesting Grasp Again")
                    # rospy.set_param("grasp_request", 1)
                    # wait_till_done("grasp_done", "Done Grasp", rate)

                    rospy.logwarn ("Requesting Trac IK")
                    rospy.set_param("lift_request", 0)
                    rospy.set_param("trac_ik_request", 1)
                    wait_till_done("trac_ik_done", "Done Trac IK", rate)

                    rospy.logwarn ("Requesting Controller")
                    rospy.set_param("skip_states", 0)
                    rospy.set_param("controller_request", 1)
                    wait_till_done("controller_done", "Done Controller", rate)
                    rospy.set_param("grasp_done", 0)
                    rospy.set_param("controller_done", 0)
                    rospy.set_param("trac_ik_done", 0)

                    rospy.logwarn ("Requesting Hand Close")
                    rospy.set_param("hand_close_request", 1)

                    # Go back to custom home state using planner
                    # if '--custom_home_state' in myargv:
                    # pose = Pose()
                    # pose.position.x, pose.position.y, pose.position.z = (0.304, -0.507, 0.795)
                    # pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w \
                    #     = (0.282, 0.155, 0.702, 0.635)
                    # pose_in_map = get_transform_pose('base_footprint', 'map', pose)
                    # rospy.Subscriber("/walker/rightLimb/joint_states", JointState, joint_state_callback)
                    rospy.logwarn ("Requesting Trac IK")
                    rospy.set_param("lift_request", 1)
                    sleep(2)
                    # go_to_custom_goal(pose_in_map, rate, "FULLBODY", controller=True)
                    rospy.set_param("trac_ik_request", 1)
                    wait_till_done("trac_ik_done", "Done Trac IK", rate)

                    rospy.logwarn ("Requesting Controller")
                    rospy.set_param("skip_states", 0)
                    rospy.set_param("controller_request", 1)
                    wait_till_done("controller_done", "Done Controller", rate)
                    rospy.set_param("controller_done", 0)
                    rospy.set_param("trac_ik_done", 0)

        rospy.logwarn ("Done Executing State Machine")
        setup_variables()

    except KeyboardInterrupt:
        print('interrupted!')
