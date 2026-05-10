import time
from typing import List, Optional

class SectorTracker:
    def __init__(self):
        self.current_sector: int = 0
        self.entry_game_time: float = 0.0
        self.tracking_valid: bool = False
        
        self.current_lap_sectors: List[float] = [0.0, 0.0, 0.0]
        self.last_lap_sectors: List[float] = [0.0, 0.0, 0.0]
        self.lap_completed_timestamp: float = -10.0
        self.last_game_time: float = 0.0

    def update(self, sector: int, game_time: float, in_pits: bool, current_wall_time: Optional[float] = None) -> None:
        self.last_game_time = game_time
        if current_wall_time is None:
            current_wall_time = time.time()
            
        if in_pits:
            self._invalidate()
            self.current_sector = sector
            return
            
        if sector == 0 or sector == self.current_sector:
            return
            
        # Sector transition logic
        prev_sector = self.current_sector
        self.current_sector = sector
        
        if prev_sector == 0:
            # First time seeing them in any sector. 
            self.entry_game_time = game_time
            # Keep tracking invalid until we do a full 3->1
        
        elif prev_sector == 3 and sector == 1:
            # Lap completed!
            if self.tracking_valid:
                # Calculate S3 time
                self.current_lap_sectors[2] = game_time - self.entry_game_time
                self.last_lap_sectors = list(self.current_lap_sectors)
                self.lap_completed_timestamp = current_wall_time
            
            # Start new lap
            self.tracking_valid = True
            self.entry_game_time = game_time
            self.current_lap_sectors = [0.0, 0.0, 0.0]
            
        elif prev_sector == 1 and sector == 2:
            if self.tracking_valid:
                self.current_lap_sectors[0] = game_time - self.entry_game_time
            self.entry_game_time = game_time
            
        elif prev_sector == 2 and sector == 3:
            if self.tracking_valid:
                self.current_lap_sectors[1] = game_time - self.entry_game_time
            self.entry_game_time = game_time
            
        else:
            # Invalid sequence (e.g., 2 -> 1, or 0 -> 2)
            # This happens if they reset to pits and drive out, or lag drops packets
            self._invalidate()

    def _invalidate(self) -> None:
        self.tracking_valid = False
        self.current_lap_sectors = [0.0, 0.0, 0.0]

    def get_display_sectors(self, current_wall_time: Optional[float] = None) -> List[float]:
        if current_wall_time is None:
            current_wall_time = time.time()
            
        if current_wall_time - self.lap_completed_timestamp <= 5.0:
            return list(self.last_lap_sectors)
            
        display_sectors = list(self.current_lap_sectors)
        if self.tracking_valid and self.current_sector in (1, 2, 3) and self.last_game_time >= self.entry_game_time:
            idx = self.current_sector - 1
            display_sectors[idx] = self.last_game_time - self.entry_game_time
            
        return display_sectors

class SectorTrackerManager:
    def __init__(self):
        self.trackers = {}  # Dict[int, SectorTracker]

    def update_driver(self, driver_idx: int, sector: int, game_time: float, in_pits: bool, current_wall_time: Optional[float] = None) -> List[float]:
        if driver_idx not in self.trackers:
            self.trackers[driver_idx] = SectorTracker()
            
        tracker = self.trackers[driver_idx]
        tracker.update(sector, game_time, in_pits, current_wall_time)
        return tracker.get_display_sectors(current_wall_time)
