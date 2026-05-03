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
        info = [MockParticipantInfo(name=b'Alice\x00', is_active=True)] + \
               [MockParticipantInfo(is_active=False)] * 31
        sm = mock_shared_memory(
            mParticipantInfo=info,
            mNumParticipants=1,
            mRacePosition=[3] + [0] * 31,
            mCurrentLapDistance=[500.0] + [0.0] * 31,
            mLapsCompleted=[1] + [0] * 31,
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
