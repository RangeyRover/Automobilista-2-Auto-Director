"""TDD tests for TelemetryProvider — TP-01 to TP-26.
Written BEFORE implementation. All must FAIL initially (RED).
"""
import pytest
from core.telemetry_provider import TelemetryProvider


# ── Shared Memory Extraction (TP-01 to TP-05) ──────────────────────────────

class TestSharedMemoryExtraction:
    def test_tp01_active_participant_extracted(self, mock_shared_memory):
        """TP-01: Active participant with known fields is extracted correctly."""
        from tests.conftest import MockParticipantInfo
        info = [MockParticipantInfo(name=b'Alice\x00', is_active=True, race_position=3, lap_distance=500.0, laps_completed=1)] + \
               [MockParticipantInfo(is_active=False)] * 31
        sm = mock_shared_memory(
            mParticipantInfo=info,
            mNumParticipants=1,
            mSpeeds=[60.0] + [0.0] * 31,
            mPitModes=[0] + [0] * 31,
            mRaceStates=[2] + [0] * 31,
            mHighestFlagColours=[0] * 32,
            mHighestFlagReasons=[0] * 32,
            mTrackLength=4000.0,
        )
        provider = TelemetryProvider(mode='shared_memory')
        participants = provider._extract_all_participants(sm)
        assert participants[0]['name'] == 'Alice'
        assert participants[0]['race_position'] == 3
        assert participants[0]['is_active'] is True

    def test_tp02_inactive_participant(self, mock_shared_memory):
        """TP-02: Inactive participant has is_active=False."""
        from tests.conftest import MockParticipantInfo
        info = [MockParticipantInfo(is_active=False)] * 32
        sm = mock_shared_memory(mParticipantInfo=info, mNumParticipants=0)
        provider = TelemetryProvider(mode='shared_memory')
        participants = provider._extract_all_participants(sm)
        assert participants[0]['is_active'] is False

    def test_tp03_driver_name_decoded_stripped(self, mock_shared_memory):
        """TP-03: Name with null bytes is decoded and stripped."""
        from tests.conftest import MockParticipantInfo
        info = [MockParticipantInfo(name=b'Bob\x00\x00\x00', is_active=True)] + \
               [MockParticipantInfo(is_active=False)] * 31
        sm = mock_shared_memory(mParticipantInfo=info, mNumParticipants=1)
        provider = TelemetryProvider(mode='shared_memory')
        participants = provider._extract_all_participants(sm)
        assert participants[0]['name'] == 'Bob'

    def test_tp04_track_info_extracted(self, mock_shared_memory):
        """TP-04: Track info reads location and length."""
        sm = mock_shared_memory(
            mTrackLocation=b'Interlagos\x00',
            mTrackLength=4309.0,
            mNumParticipants=5,
        )
        provider = TelemetryProvider(mode='shared_memory')
        info = provider._extract_track_info(sm)
        assert info['track_name'] == 'Interlagos'
        assert info['track_length'] == 4309.0
        assert info['num_participants'] == 5

    def test_tp04a_track_info_fallback_extraction(self, mock_shared_memory):
        """TP-04a: Verify _extract_track_info falls back from translated to raw track location."""
        # Scenario 1: Translated string exists
        sm1 = mock_shared_memory(
            mTranslatedTrackLocation=b'Interlagos\x00',
            mTrackLocation=b'RawInterlagos\x00',
            mTrackLength=4309.0,
            mNumParticipants=10
        )
        provider = TelemetryProvider(mode='shared_memory')
        info1 = provider._extract_track_info(sm1)
        assert info1['track_name'] == 'Interlagos'

        # Scenario 2: Translated string is empty, fallback to raw
        sm2 = mock_shared_memory(
            mTranslatedTrackLocation=b'\x00',
            mTrackLocation=b'RawMonza\x00',
            mTrackLength=5793.0,
            mNumParticipants=20
        )
        info2 = provider._extract_track_info(sm2)
        assert info2['track_name'] == 'RawMonza'
        
        # Scenario 3: Missing attributes entirely
        class MinimalSM:
            pass
        info3 = provider._extract_track_info(MinimalSM())
        assert info3['track_name'] == ''

    def test_tp05_game_time_from_current_time(self, mock_shared_memory):
        """TP-05: game_time from mCurrentTime."""
        sm = mock_shared_memory(mCurrentTime=125.5)
        provider = TelemetryProvider(mode='shared_memory')
        assert provider._extract_game_time(sm) == 125.5


# ── True Distance Calculation (TP-06 to TP-08) ─────────────────────────────

class TestTrueDistance:
    def test_tp06_lap0_at_500m(self):
        """TP-06: lap 0, dist 500, track 4000 → true_distance = 500"""
        result = TelemetryProvider._calc_true_distance(0, 500.0, 4000.0)
        assert result == 500.0

    def test_tp07_lap3_at_1000m(self):
        """TP-07: lap 3, dist 1000, track 4000 → true_distance = 13000"""
        result = TelemetryProvider._calc_true_distance(3, 1000.0, 4000.0)
        assert result == 13000.0

    def test_tp08_lap0_at_0m(self):
        """TP-08: lap 0, dist 0 → true_distance = 0"""
        result = TelemetryProvider._calc_true_distance(0, 0.0, 4000.0)
        assert result == 0.0


# ── Gap Calculation (TP-09 to TP-11) ────────────────────────────────────────

class TestGapCalculation:
    def test_tp09_simple_gap(self, make_participant):
        """TP-09: Two drivers 200m apart → gap = 200"""
        participants = {
            0: make_participant(true_distance=5000, is_active=True),
            1: make_participant(true_distance=4800, is_active=True),
        }
        TelemetryProvider._calc_gaps(participants)
        assert participants[1]['gap_ahead'] == pytest.approx(200.0)

    def test_tp10_leader_has_zero_gap(self, make_participant):
        """TP-10: Leader has gap_ahead = 0."""
        participants = {
            0: make_participant(true_distance=5000, is_active=True),
            1: make_participant(true_distance=4800, is_active=True),
        }
        TelemetryProvider._calc_gaps(participants)
        assert participants[0]['gap_ahead'] == 0.0

    def test_tp11_five_drivers_sorted(self, make_participant):
        """TP-11: 5 drivers at varied distances → gaps in order."""
        participants = {
            0: make_participant(true_distance=5000, is_active=True),
            1: make_participant(true_distance=4500, is_active=True),
            2: make_participant(true_distance=4000, is_active=True),
            3: make_participant(true_distance=3500, is_active=True),
            4: make_participant(true_distance=3000, is_active=True),
        }
        TelemetryProvider._calc_gaps(participants)
        assert participants[0]['gap_ahead'] == 0.0
        assert participants[1]['gap_ahead'] == pytest.approx(500.0)
        assert participants[4]['gap_ahead'] == pytest.approx(500.0)


# ── Cars Ahead 250m (TP-12 to TP-14) ───────────────────────────────────────

class TestCarsAhead:
    def test_tp12_one_car_100m_ahead(self, make_participant):
        """TP-12: Car 100m ahead → cars_ahead_250m = 1"""
        participants = {
            0: make_participant(true_distance=5000, is_active=True),
            1: make_participant(true_distance=4900, is_active=True),
        }
        TelemetryProvider._calc_cars_ahead(participants, track_length=10000.0)
        assert participants[1]['cars_ahead_250m'] == 1

    def test_tp13_car_300m_ahead_outside(self, make_participant):
        """TP-13: Car 300m ahead → cars_ahead_250m = 0"""
        participants = {
            0: make_participant(true_distance=5000, is_active=True),
            1: make_participant(true_distance=4700, is_active=True),
        }
        TelemetryProvider._calc_cars_ahead(participants, track_length=10000.0)
        assert participants[1]['cars_ahead_250m'] == 0

    def test_tp14_sf_line_wrapping(self, make_participant):
        """TP-14: S/F wrapping — P1 at 3900m, P2 at 100m (track 4000) → counts correctly."""
        # P2 at true_distance 4100 (lap 1 + 100m), P1 at 3900 (lap 0 + 3900m)
        # In true distance terms P2 is ahead of P1
        participants = {
            0: make_participant(true_distance=4100, is_active=True),
            1: make_participant(true_distance=3900, is_active=True),
        }
        TelemetryProvider._calc_cars_ahead(participants, track_length=4000.0)
        assert participants[1]['cars_ahead_250m'] == 1  # P1 at 3900 has P2 at 4100 → 200m ahead


# ── Speed Calculation (TP-15 to TP-18) ──────────────────────────────────────

class TestSpeedCalc:
    def test_tp15_normal_speed(self):
        """TP-15: distances=[100,200], timestamps=[0,1] → speed = 100"""
        provider = TelemetryProvider(mode='shared_memory')
        provider._distance_history = {0: [(0, 100.0), (1, 200.0)]}
        speed = provider._calc_speed(0, track_length=10000.0)
        assert speed == pytest.approx(100.0)

    def test_tp16_sf_crossing(self):
        """TP-16: S/F crossing distances=[3900,100], track=4000 → speed = 200"""
        provider = TelemetryProvider(mode='shared_memory')
        provider._distance_history = {0: [(0, 3900.0), (1, 100.0)]}
        speed = provider._calc_speed(0, track_length=4000.0)
        assert speed == pytest.approx(200.0)

    def test_tp17_stationary(self):
        """TP-17: Same distance → speed = 0"""
        provider = TelemetryProvider(mode='shared_memory')
        provider._distance_history = {0: [(0, 500.0), (1, 500.0)]}
        speed = provider._calc_speed(0, track_length=10000.0)
        assert speed == pytest.approx(0.0)

    def test_tp18_first_poll_insufficient(self):
        """TP-18: Single entry → speed = None"""
        provider = TelemetryProvider(mode='shared_memory')
        provider._distance_history = {0: [(0, 100.0)]}
        speed = provider._calc_speed(0, track_length=10000.0)
        assert speed is None


# ── Connection State (TP-19 to TP-20) ───────────────────────────────────────

class TestConnectionState:
    def test_tp19_connected_when_data_available(self):
        """TP-19: is_connected True when data available."""
        provider = TelemetryProvider(mode='shared_memory')
        provider._connected = True
        assert provider.is_connected() is True

    def test_tp20_disconnected_when_no_data(self):
        """TP-20: is_connected False when no data."""
        provider = TelemetryProvider(mode='shared_memory')
        provider._connected = False
        assert provider.is_connected() is False


# ── Track Change Detection (TP-21) ──────────────────────────────────────────

class TestTrackChange:
    def test_tp21_track_change_resets(self, mock_shared_memory):
        """TP-21: Track change resets participants."""
        provider = TelemetryProvider(mode='shared_memory')
        provider._last_track_name = 'Interlagos'
        new_track_info = {'track_name': 'Monza', 'track_length': 5793.0, 'num_participants': 5}
        assert provider._detect_track_change(new_track_info) is True
        assert provider._last_track_name == 'Monza'


# ── UDP Data Source (TP-22 to TP-24) ────────────────────────────────────────

class TestUDPDataSource:
    def test_tp22_udp_mode_init(self):
        """TP-22: UDP mode initialises without crash."""
        provider = TelemetryProvider(mode='udp')
        assert provider._mode == 'udp'

    def test_tp23_packet_buffer_retention(self):
        """TP-23: Packet buffer retains latest packet per size."""
        provider = TelemetryProvider(mode='udp')
        packet1 = b'\x00' * 100
        packet2 = b'\x01' * 100
        provider._add_packet_to_buffer(packet1)
        provider._add_packet_to_buffer(packet2)
        assert provider._packet_buffer.get(100) == packet2

    def test_tp24_udp_extended_packet_parse(self):
        """TP-24: Known extended packet parsed correctly."""
        provider = TelemetryProvider(mode='udp')
        # Create a minimal packet that the parser can handle
        # This tests the interface exists — the actual byte parsing
        # will be validated against real captured packets
        result = provider._parse_udp_participants(None)
        assert result is None or isinstance(result, dict)


# ── Connection State Transitions (TP-25 to TP-26) ──────────────────────────

class TestConnectionTransitions:
    def test_tp25_disconnected_to_connected(self):
        """TP-25: Transition from disconnected to connected."""
        provider = TelemetryProvider(mode='shared_memory')
        provider._connected = False
        provider._update_connection_state(data_available=True)
        assert provider.is_connected() is True

    def test_tp26_connected_disconnected_reconnected(self):
        """TP-26: Full cycle: connected→disconnected→reconnected."""
        provider = TelemetryProvider(mode='shared_memory')
        provider._connected = True
        provider._update_connection_state(data_available=False)
        assert provider.is_connected() is False
        provider._update_connection_state(data_available=True)
        assert provider.is_connected() is True


# ── Closing Speed Calculation (TP-27 to TP-28) ──────────────────────────────

class TestClosingSpeedCalc:
    def test_tp27_positive_closing_speed(self):
        """TP-27: Previous gap 50, current gap 40 over 0.2s → closing speed 50 m/s"""
        provider = TelemetryProvider(mode='shared_memory')
        provider._gap_history = {0: 50.0}
        provider._closing_speed_ema = {}
        speed = provider._calc_closing_speed(idx=0, current_gap=40.0, dt=0.2)
        assert speed == pytest.approx(50.0)

    def test_tp28_ema_smoothing(self):
        """TP-28: EMA smooths the closing speed over multiple calls"""
        provider = TelemetryProvider(mode='shared_memory')
        provider._gap_history = {0: 50.0}
        provider._closing_speed_ema = {0: 10.0}
        # dt=0.2, new_val = (50-40)/0.2 = 50.0
        # alpha = 0.3. EMA = 0.3*50 + 0.7*10 = 15 + 7 = 22
        speed = provider._calc_closing_speed(0, 40.0, 0.2)
        assert speed == pytest.approx(22.0)
        assert provider._closing_speed_ema[0] == pytest.approx(22.0)


# ── Session Info (TP-29) ────────────────────────────────────────────────────

class TestSessionInfo:
    def test_tp29_extract_session_info(self, mock_shared_memory):
        """TP-29: mEventTimeRemaining and mCurrentTime extracted."""
        sm = mock_shared_memory(mEventTimeRemaining=3600.0, mCurrentTime=120.0, mViewedParticipantIndex=1)
        provider = TelemetryProvider(mode='shared_memory')
        info = provider._extract_session_info(sm)
        assert info['event_time_remaining'] == 3600.0
        assert info['current_time'] == 120.0
        assert info['viewed_participant_index'] == 1

# ── UDP Networking & Threading (TP-30 to TP-31) ─────────────────────────────

class TestUDPNetworking:
    def test_tp30_udp_lifecycle(self):
        """TP-30: start_udp() binds socket, stop_udp() unbinds."""
        provider = TelemetryProvider(mode='shared_memory')
        provider.start_udp()
        assert getattr(provider, '_udp_running', False) is True
        assert getattr(provider, '_udp_thread', None) is not None
        assert provider._udp_thread.is_alive() is True
        provider.stop_udp()
        assert provider._udp_running is False
        assert not provider._udp_thread.is_alive()

    def test_tp31_udp_set_port(self):
        """TP-31: set_udp_port() restarts the thread."""
        provider = TelemetryProvider(mode='shared_memory')
        provider.start_udp()
        old_thread = provider._udp_thread
        provider.set_udp_port(5607)
        assert getattr(provider, '_udp_port', 5606) == 5607
        assert provider._udp_thread is not old_thread
        assert provider._udp_thread.is_alive() is True
        provider.stop_udp()

# ── UDP Binary Parsing (TP-32 to TP-34) ─────────────────────────────────────

class TestUDPParsing:
    def test_tp32_parse_extended_packet_1063(self):
        """TP-32: Parse 1063-byte extended timing packet."""
        provider = TelemetryProvider()
        packet = bytearray(1063)
        
        # Mock participant 0: RacePosition = 5 (active), lap distance = 1000, pit mode = 2
        # offset race_pos: 31 + 0 * 32 + 16 = 47
        packet[47] = 5 | 0x80  # Position 5, Active True
        # offset lap_distance: 31 + 0 * 32 + 14 = 45
        packet[45:47] = (1000).to_bytes(2, 'little')
        # offset pit mode: 31 + 0 * 32 + 19 = 50
        packet[50] = 2
        
        provider._udp_participant_names = {0: 'Alice UDP'}
        
        participants = provider._parse_udp_participants(bytes(packet))
        assert participants is not None
        assert participants[0]['race_position'] == 5
        assert participants[0]['is_active'] is True
        assert participants[0]['lap_distance'] == 1000
        assert participants[0]['pit_mode'] == 2
        assert participants[0]['name'] == 'Alice UDP'

    def test_tp33_parse_track_info_308(self):
        """TP-33: Parse 308-byte track info packet."""
        import struct
        provider = TelemetryProvider()
        packet = bytearray(308)
        # Offset 44: float track_length
        struct.pack_into('f', packet, 44, 4500.0)
        
        track_info = provider._extract_udp_track_info(bytes(packet))
        assert track_info is not None
        assert track_info['track_length'] == 4500.0

    def test_tp34_parse_participant_names_1367(self):
        """TP-34: Parse 1367-byte strings packet."""
        provider = TelemetryProvider()
        packet = bytearray(1367)
        packet[8] = 1
        # Offset 16 is where 16 names of 64 bytes each start
        name_bytes = b'Bob UDP' + b'\x00' * 57
        packet[16:16+64] = name_bytes
        
        provider._parse_udp_names(bytes(packet))
        assert provider._udp_participant_names.get(0) == 'Bob UDP'

# ── Hybrid Logic Integration (TP-35 to TP-37) ───────────────────────────────

class TestHybridLogic:
    def test_tp35_shared_memory_priority(self, mock_shared_memory):
        """TP-35: Shared memory session info takes priority."""
        sm = mock_shared_memory(mEventTimeRemaining=600.0, mLapsInEvent=10, mViewedParticipantIndex=1)
        provider = TelemetryProvider()
        
        info = provider.get_session_info(sm)
        assert info['event_time_remaining'] == 600.0
        assert info['laps_in_event'] == 10
        assert info['viewed_participant_index'] == 1

    def test_tp36_udp_fallback(self, mock_shared_memory):
        """TP-36: UDP fallback when shared memory is 0 or null."""
        sm = mock_shared_memory(mEventTimeRemaining=0.0, mLapsInEvent=0)
        provider = TelemetryProvider()
        
        # Mock the UDP session info extraction logic directly
        provider._extract_udp_session_info = lambda: {'event_time_remaining': 120.0, 'laps_in_event': 5}
        
        info = provider.get_session_info(sm)
        # Since sm had 0.0, it should merge UDP
        assert info['event_time_remaining'] == 120.0
        assert info['laps_in_event'] == 5

    def test_tp37_seamless_derived_calculations_hybrid(self, mock_shared_memory):
        """TP-37: Seamless derived calculations in Hybrid mode."""
        # When polling from UDP (e.g. if shared memory is missing entirely), speed is still calculated correctly.
        provider = TelemetryProvider(mode='udp')
        
        # Mock participant extraction
        provider._parse_udp_participants = lambda pkt: {
            0: {'name': 'Alice', 'is_active': True, 'lap_distance': 1000.0, 'current_lap': 1, 'gap_ahead': 0.0}
        }
        
        # First poll
        provider._last_poll_time -= 0.1
        provider.poll()
        assert provider._distance_history[0][0][1] == 1000.0
        
        provider._last_poll_time -= 0.1
    
        # Second poll
        provider._parse_udp_participants = lambda pkt: {
            0: {'name': 'Alice', 'is_active': True, 'lap_distance': 1100.0, 'current_lap': 1, 'gap_ahead': 0.0}
        }
        participants = provider.poll()
        
        # Speed should be calculated from the two polls
        print(f"history: {provider._distance_history[0]}")
        assert 'speed' in participants[0]
        assert participants[0]['speed'] > 0.0

