import tkinter as tk
from core.gui_builder import GUIBuilder

def test_gui_builder_initialisation():
    """T047: Verify GUIBuilder can be imported and initialized."""
    root = tk.Tk()
    
    # Mock the app
    class MockApp:
        def __init__(self):
            self.root = root
            self._mode = 'shared_memory'
            self._user_mode = 'hybrid'
            self._effective_source = 'hybrid'
            self._director_enabled = False
            self._switch_interval = 7.0
            self._camera_close_gap = 0.5
            self._sweep_dwell_time = 1.0
            self._auto_switch_counter = 0
            self._participants = {}
            
            # tkinter variables
            self.lbl_telemetry_status = None
            self.lbl_hybrid_status = None
            self.lbl_camera_status = None
            self.tree = None
            
        def toggle_director(self):
            pass
            
        def get_current_camera_type(self):
            return "roof"
            
        def _update_settings(self, *args):
            pass

        def set_mode(self, mode):
            pass

        def trigger_sweep(self):
            pass
            
    app = MockApp()
    builder = GUIBuilder(app)
    
    # Test UI building
    builder.build_ui()
    
    assert app.lbl_connection is not None
    assert app.lbl_director is not None
    assert app.lbl_camera is not None
    assert app.tree is not None
    
    # We won't test update_grid yet, just assert it exists
    assert hasattr(builder, 'update_grid')
    
    root.destroy()
