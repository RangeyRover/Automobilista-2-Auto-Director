import re

class TimelineParser:
    """Parses AMS2 Replay Log files to inject narrative events into V4 ScoringEngine."""
    
    def __init__(self):
        # 02:09.41 - Accident involving: Ludwig
        self.re_time = re.compile(r"^(\d{2}):(\d{2}\.\d{2}) - ")
        self.re_accident = re.compile(r"Accident involving: (.+?)(?: \(P(\d+)\))?$")
        self.re_overtake = re.compile(r"Overtake! (.+?)(?: \(P\d+\))? overtook (.+?)(?: \(P\d+\))? for position (\d+)$")
        self.re_total_time = re.compile(r"Total Session Time: (\d{2}):(\d{2}\.\d{2})")
        self.re_leader_laps = re.compile(r"Leader Laps Completed: (\d+)")
        
        # Additive scoring overrides for V4
        self.accident_base_score = 6.0
        self.accident_duration = 15.0
        
        self.overtake_base_score = 4.0
        self.overtake_duration = 12.0
        
    def parse_line(self, line: str):
        """Parses a log line into a memory event dictionary. Returns None if invalid or ignored."""
        
        time_total_match = self.re_total_time.search(line)
        if time_total_match:
            minutes = int(time_total_match.group(1))
            seconds = float(time_total_match.group(2))
            return {
                'type': 'Total Session Time',
                'timestamp': (minutes * 60) + seconds
            }

        laps_match = self.re_leader_laps.search(line)
        if laps_match:
            # The legacy race_analyser logged mCurrentLap *after* the race finished (which was +1).
            # Subtract 1 to get the actual number of laps in the event.
            return {
                'type': 'Leader Laps Completed',
                'lap': int(laps_match.group(1)) - 1
            }

        time_match = self.re_time.match(line)
        if not time_match:
            return None
            
        minutes = int(time_match.group(1))
        seconds = float(time_match.group(2))
        timestamp = (minutes * 60) + seconds
        
        event_str = line[time_match.end():]
        
        # 1. Accident
        acc_match = self.re_accident.match(event_str)
        if acc_match:
            return {
                'type': 'Accident',
                'timestamp': timestamp,
                'target_driver': acc_match.group(1),
                'base_score': self.accident_base_score,
                'duration': self.accident_duration
            }
            
        # 2. Overtake
        ov_match = self.re_overtake.match(event_str)
        if ov_match:
            return {
                'type': 'Overtake',
                'timestamp': timestamp,
                'target_driver': ov_match.group(1),
                'target_driver_2': ov_match.group(2),
                'base_score': self.overtake_base_score,
                'duration': self.overtake_duration
            }
            
        return None
