#!/usr/bin/env python
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
Object crash without prior vehicle action scenario:
The scenario realizes the user controlled ego vehicle
moving along the road and encountering a cyclist ahead.
"""

import py_trees

from srunner.scenariomanager.atomic_scenario_behavior import *
from srunner.scenariomanager.atomic_scenario_criteria import *
from srunner.scenariomanager.timer import TimeOut
from srunner.scenarios.basic_scenario import *
from srunner.scenarios.config_parser import ActorConfigurationData
from srunner.scenarios.scenario_helper import get_location_in_distance

OBJECT_CROSSING_SCENARIOS = [
    "StationaryObjectCrossing",
    "DynamicObjectCrossing"
]


class StationaryObjectCrossing(BasicScenario):

    """
    This class holds everything required for a simple object crash
    without prior vehicle action involving a vehicle and a cyclist.
    The ego vehicle is passing through a road and encounters
    a stationary cyclist.
    """

    category = "ObjectCrossing"

    timeout = 60

    # ego vehicle parameters
    _ego_vehicle_velocity_allowed = 20
    _ego_vehicle_distance_to_other = 35

    def __init__(self, world, ego_vehicle, config, randomize=False, debug_mode=False, criteria_enable=True):
        """
        Setup all relevant parameters and create scenario
        """
        super(StationaryObjectCrossing, self).__init__("Stationaryobjectcrossing",
                                                       ego_vehicle,
                                                       config,
                                                       world,
                                                       debug_mode,
                                                       criteria_enable=criteria_enable)


        _start_distance = 40
        actor_parameters = []
        world_map = ego_vehicle.get_world().get_map()
        lane_width = world_map.get_waypoint(ego_vehicle.get_location()).lane_width
        location, _ = get_location_in_distance(ego_vehicle, _start_distance)
        waypoint = world_map.get_waypoint(location)
        model = 'vehicle.diamondback.century'
        offset = {"orientation": 270, "position": 90, "z": 0.2, "k": 0.2}
        position_yaw = waypoint.transform.rotation.yaw + offset['position']
        orientation_yaw = waypoint.transform.rotation.yaw + offset['orientation']
        offset_location = carla.Location(
            offset['k']*lane_width*math.cos(math.radians(position_yaw)),
            offset['k']*lane_width*math.sin(math.radians(position_yaw)))
        location += offset_location
        location.z += offset['z']
        transform = carla.Transform(location, carla.Rotation(yaw=orientation_yaw))
        actor_parameters.append(ActorConfigurationData(model, transform))

        super(StationaryObjectCrossing, self).__init__("Stationaryobjectcrossing",
                                                       ego_vehicle,
                                                       actor_parameters,
                                                       town,
                                                       world,
                                                       debug_mode)

    def _create_behavior(self):
        """
        Only behavior here is to wait
        """
        redundant = TimeOut(self.timeout - 5)
        return redundant

    def _create_test_criteria(self):
        """
        A list of all test criteria will be created that is later used
        in parallel behavior tree.
        """
        criteria = []

        collision_criterion = CollisionTest(self.ego_vehicle)
        criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        """
        Remove all actors upon deletion
        """
        self.remove_all_actors()

class DynamicObjectCrossing(BasicScenario):

    """
    This class holds everything required for a simple object crash
    without prior vehicle action involving a vehicle and a cyclist,
    The ego vehicle is passing through a road,
    And encounters a cyclist crossing the road.
    """


    category = "ObjectCrossing"

    timeout = 60

    # ego vehicle parameters
    _ego_vehicle_velocity_allowed = 10
    _ego_vehicle_distance_driven = 50

    # other vehicle parameters
    _other_actor_target_velocity = 10
    _other_actor_max_brake = 1.0
    _time_to_reach = 12

    def __init__(self, world, ego_vehicle, config, randomize=False, debug_mode=False, criteria_enable=True):
        """
        Setup all relevant parameters and create scenario
        """
        category = "ObjectCrossing"
        timeout = 60

        super(DynamicObjectCrossing, self).__init__("Dynamicobjectcrossing",
                                                    ego_vehicle,
                                                    config,
                                                    world,
                                                    debug_mode,
                                                    criteria_enable=criteria_enable)

        # other vehicle parameters
        _other_actor_target_velocity = 10
        _other_actor_max_brake = 1.0
        _time_to_reach = 12

        # spawning other actors
        _start_distance = 40
        actor_parameters = []
        world_map = ego_vehicle.get_world().get_map()
        lane_width = world_map.get_waypoint(ego_vehicle.get_location()).lane_width
        location, _ = get_location_in_distance(ego_vehicle, _start_distance)
        waypoint = world_map.get_waypoint(location)
        model = 'vehicle.diamondback.century'
        offset = {"orientation": 270, "position": 90, "z": 0.2, "k": 1.1}
        position_yaw = waypoint.transform.rotation.yaw + offset['position']
        orientation_yaw = waypoint.transform.rotation.yaw + offset['orientation']
        offset_location = carla.Location(
            offset['k']*lane_width*math.cos(math.radians(position_yaw)),
            offset['k']*lane_width*math.sin(math.radians(position_yaw)))
        location += offset_location
        location.z += offset['z']
        transform = carla.Transform(location, carla.Rotation(yaw=orientation_yaw))
        actor_parameters.append(ActorConfigurationData(model, transform))

        super(DynamicObjectCrossing, self).__init__("Dynamicobjectcrossing",
                                                    ego_vehicle,
                                                    actor_parameters,
                                                    town,
                                                    world,
                                                    debug_mode)

    def _create_behavior(self):
        """
        After invoking this scenario, cyclist will wait for the user
        controlled vehicle to enter trigger distance region,
        the cyclist starts crossing the road once the condition meets,
        then after 60 seconds, a timeout stops the scenario
        """

        lane_width = self.ego_vehicle.get_world().get_map().get_waypoint(self.ego_vehicle.get_location()).lane_width
        lane_width = lane_width+(1.25*lane_width)

        # leaf nodes
        start_condition = InTimeToArrivalToVehicle(self.other_actors[0], self.ego_vehicle, self._time_to_reach)
        actor_velocity = KeepVelocity(self.other_actors[0], self._other_actor_target_velocity)
        actor_drive = DriveDistance(self.other_actors[0], 0.3*lane_width)
        actor_start_cross_lane = AccelerateToVelocity(self.other_actors[0], 1.0,
                                                      self._other_actor_target_velocity)
        actor_cross_lane = DriveDistance(self.other_actors[0], lane_width)
        actor_stop_crossed_lane = StopVehicle(self.other_actors[0], self._other_actor_max_brake)
        timeout_other_actor = TimeOut(5)

        # non leaf nodes
        root = py_trees.composites.Parallel(
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE)
        scenario_sequence = py_trees.composites.Sequence()
        keep_velocity_other = py_trees.composites.Parallel(
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE)
        keep_velocity = py_trees.composites.Parallel(
            policy=py_trees.common.ParallelPolicy.SUCCESS_ON_ONE)

        # building tree
        root.add_child(scenario_sequence)
        scenario_sequence.add_child(HandBrakeVehicle(self.other_actors[0], True))
        scenario_sequence.add_child(start_condition)
        scenario_sequence.add_child(HandBrakeVehicle(self.other_actors[0], False))
        scenario_sequence.add_child(keep_velocity)
        scenario_sequence.add_child(keep_velocity_other)
        scenario_sequence.add_child(actor_stop_crossed_lane)
        scenario_sequence.add_child(timeout_other_actor)

        keep_velocity.add_child(actor_velocity)
        keep_velocity.add_child(actor_drive)
        keep_velocity_other.add_child(actor_start_cross_lane)
        keep_velocity_other.add_child(actor_cross_lane)

        return root

    def _create_test_criteria(self):
        """
        A list of all test criteria will be created that is later used
        in parallel behavior tree.
        """
        criteria = []

        collision_criterion = CollisionTest(self.ego_vehicle)
        criteria.append(collision_criterion)

        return criteria

    def __del__(self):
        """
        Remove all actors upon deletion
        """
        self.remove_all_actors()