import pytest
from core.camera_controller import CameraController, CAMERA_SET_MAP

def test_camera_type_default_is_tv_cam():
    controller = CameraController(None, None)
    assert controller.current_camera_type == "tv_cam"

def test_camera_type_updates_on_set():
    controller = CameraController(None, None)
    controller.current_camera_type = "cockpit"
    assert controller.current_camera_type == "cockpit"

def test_camera_set_mappings():
    expected = {
        "Cockpit": "cockpit", 
        "Helmet": "cockpit", 
        "TV Pod": "cockpit", 
        "TV Cam 1": "tv_cam", 
        "TV Cam 2": "tv_cam", 
        "TV Cam 3": "tv_cam", 
        "Chase Near": "chase", 
        "Chase Far": "chase", 
        "Chase Bumper": "chase"
    }
    assert CAMERA_SET_MAP == expected

def test_update_camera_type():
    controller = CameraController(None, None)
    controller.update_camera_type("Helmet")
    assert controller.current_camera_type == "cockpit"
    controller.update_camera_type("TV Cam 1")
    assert controller.current_camera_type == "tv_cam"
    controller.update_camera_type("Unknown Cam")
    assert controller.current_camera_type == "tv_cam"
