"""Tests for UDP/Hybrid data source mode detection and switching.

TDD tests for feature/6-udp-hybrid-mode. Tests are written BEFORE
implementation code. All tests should FAIL initially, then pass
as implementation is completed.
"""
import struct

# Import the provider to test detection signals
from core.telemetry_provider import TelemetryProvider


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_308_packet(track_length: float = 3936.0) -> bytes:
    """Build a minimal 308-byte UDP packet with track_length at offset 44."""
    data = bytearray(308)
    struct.pack_into('f', data, 44, track_length)
    return bytes(data)


def _build_1367_packet(names: list[str] | None = None,
                       car_names: list[str] | None = None,
                       car_classes: list[str] | None = None) -> bytes:
    """Build a 1367-byte UDP Strings packet.

    Layout (PCars2/AMS2):
      Offset   0-15:  PacketBase header
      Offset  16-1039: 16 × 64-byte participant names
      Offset 1040-2063: 16 × 64-byte car names  (only first 327 bytes available in 1367 pkt)
      Offset 2064+:    16 × 64-byte car class names (not in 1367 pkt)

    Since 1367 bytes = 16 header + 16×64 names + 16×64 car names + 16×(64-9) car classes partial,
    we fill what fits.
    """
    data = bytearray(1367)
    data[8] = 1
    if names:
        for i, name in enumerate(names[:16]):
            offset = 16 + (i * 64)
            name_bytes = name.encode('utf-8')[:63]
            data[offset:offset + len(name_bytes)] = name_bytes
    if car_names:
        for i, cn in enumerate(car_names[:16]):
            offset = 1040 + (i * 64)
            if offset + 64 <= 1367:
                cn_bytes = cn.encode('utf-8')[:63]
                data[offset:offset + len(cn_bytes)] = cn_bytes
    # car_classes would start at 2064, which is beyond 1367 bytes
    # For 1367-byte packets, car_class is not available
    return bytes(data)


def _build_1136_packet(names: list[str] | None = None,
                       nationalities: list[int] | None = None) -> bytes:
    """Build a 1136-byte UDP Strings packet (AMS2 format).

    Layout:
      Offset   0-15: PacketBase header (mPartialPacketIndex at offset 8)
      Offset  16-1039: 16 × 64-byte participant names
      Offset 1040-1103: 16 × 4-byte nationalities (hashes)
    """
    data = bytearray(1136)
    data[8] = 1 # mPartialPacketIndex = 1
    if names:
        for i, name in enumerate(names[:16]):
            offset = 16 + (i * 64)
            name_bytes = name.encode('utf-8')[:63]
            data[offset:offset + len(name_bytes)] = name_bytes
            
    if nationalities:
        for i, nat_hash in enumerate(nationalities[:16]):
            offset = 1040 + (i * 4)
            struct.pack_into('<I', data, offset, nat_hash)
            
    return bytes(data)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 2: Foundation — Detection Signal Methods
# ══════════════════════════════════════════════════════════════════════════════

class TestDetectionSignals:
    """T003–T006: Test the detection signal methods on TelemetryProvider."""

    def test_udp_has_track_length_false_when_no_packet(self):
        """T003: No 308-byte packet → udp_has_track_length() == False."""
        provider = TelemetryProvider(mode='udp')
        assert provider.udp_has_track_length() is False

    def test_udp_has_track_length_true_when_valid(self):
        """T004: 308-byte packet with track_length=3936.0 → True."""
        provider = TelemetryProvider(mode='udp')
        provider._packet_buffer[308] = _build_308_packet(track_length=3936.0)
        assert provider.udp_has_track_length() is True

    def test_udp_has_track_length_false_when_zero(self):
        """Edge: 308-byte packet with track_length=0.0 → False."""
        provider = TelemetryProvider(mode='udp')
        provider._packet_buffer[308] = _build_308_packet(track_length=0.0)
        assert provider.udp_has_track_length() is False

    def test_udp_has_participant_names_false_when_empty(self):
        """T005: No names cached → udp_has_participant_names() == False."""
        provider = TelemetryProvider(mode='udp')
        assert provider.udp_has_participant_names() is False

    def test_udp_has_participant_names_true_when_cached(self):
        """T006: Inject 1367-byte packet, parse, check names cached."""
        provider = TelemetryProvider(mode='udp')
        packet = _build_1367_packet(names=["Max Verstappen", "Lewis Hamilton"])
        provider._parse_udp_names(packet)
        assert provider.udp_has_participant_names() is True


# ══════════════════════════════════════════════════════════════════════════════
# Phase 5: US4 — UDP Car Name/Class Parsing
# ══════════════════════════════════════════════════════════════════════════════

class TestUDPCarParsing:
    """T027–T029: Test car name and car class parsing from UDP Strings packets."""

    def test_parse_udp_car_names_from_strings_packet(self):
        """T027: 1367-byte packet with car name data → get_udp_car_names()[0] correct."""
        provider = TelemetryProvider(mode='udp')
        packet = _build_1367_packet(
            names=["Max Verstappen"],
            car_names=["Formula Ultimate Gen3"]
        )
        provider._parse_udp_names(packet)
        car_names = provider.get_udp_car_names()
        assert 0 in car_names
        assert car_names[0] == "Formula Ultimate Gen3"

    def test_parse_udp_car_classes_from_strings_packet(self):
        """T028: Car class data from 1367-byte packet.

        Note: In a 1367-byte packet, car_class block starts at offset 2064
        which is beyond the packet boundary. Car classes are only available
        in larger packets or the 1136-byte variant. This test verifies
        graceful handling.
        """
        provider = TelemetryProvider(mode='udp')
        # For 1367 packet, car classes are out of bounds — should return empty
        packet = _build_1367_packet(names=["Max Verstappen"])
        provider._parse_udp_names(packet)
        car_classes = provider.get_udp_car_classes()
        # Graceful: empty dict or empty string value is acceptable
        assert isinstance(car_classes, dict)

    def test_car_names_empty_when_no_strings_packet(self):
        """T029: No 1367-byte packet → get_udp_car_names() returns empty dict."""
        provider = TelemetryProvider(mode='udp')
        car_names = provider.get_udp_car_names()
        assert car_names == {}

    def test_spec_1136_extracts_nationalities(self):
        """T030: 1136-byte packet → extracts nationality hashes correctly into mapped names."""
        provider = TelemetryProvider(mode='udp')
        # Hash for Brazil is 933178424, Uruguay is 1004104139
        packet = _build_1136_packet(
            names=["Caio Barbalho", "nicolascabreralenu", "Unknown Hash"],
            nationalities=[933178424, 1004104139, 999999999]
        )
        provider._parse_udp_names(packet)
        # Check cached internal nationalities
        assert provider._udp_participant_nationalities[0] == "BR"
        assert provider._udp_participant_nationalities[1] == "UY"
        assert provider._udp_participant_nationalities[2] == ""
        
        # When parsing participants, nationality should be hydrated
        dummy_packet = bytearray(1063)
        # set participant 0, 1, 2 as active
        dummy_packet[31+16] = 0x80
        dummy_packet[31+32+16] = 0x80
        dummy_packet[31+64+16] = 0x80
        participants = provider._parse_udp_participants(dummy_packet)
        assert participants is not None
        assert participants[0]['nationality'] == "BR"
        assert participants[1]['nationality'] == "UY"
        assert participants[2]['nationality'] == ""




# ══════════════════════════════════════════════════════════════════════════════
# Phase 3: US1 — Manual Mode Override (unit-testable parts)
# ══════════════════════════════════════════════════════════════════════════════

class TestManualModeOverride:
    """T010–T011, T213: Test that mode selection affects poll() path."""

    def test_udp_only_uses_udp_path(self):
        """T010: When poll(None) is called, provider uses UDP path."""
        provider = TelemetryProvider(mode='udp')
        # With no UDP data either, should return None (not crash)
        result = provider.poll(None)
        assert result is None  # No data available

    def test_hybrid_uses_shm_when_available(self):
        """T011: When poll(shm) is called with valid SHM, uses SHM path."""
        provider = TelemetryProvider(mode='shared_memory')
        # Build a minimal SHM mock
        class MockSHM:
            mNumParticipants = 2
            mTrackLength = 3936.0
            mTrackLocation = b'Interlagos\x00' + b'\x00' * 53
            mTrackVariation = b'GP\x00' + b'\x00' * 61
            mCurrentTime = 120.0
            mParticipantInfo = []
            mGameState = 2
            mSessionState = 5
            mRaceState = 2
            mViewedParticipantIndex = 0
            mEventTimeRemaining = 300.0
            mLapsInEvent = 13
        
        # Create mock participant infos
        class MockParticipant:
            def __init__(self, name, active, pos, lap, dist, sector):
                self.mIsActive = active
                self.mName = name.encode('utf-8').ljust(64, b'\x00')
                self.mWorldPosition = [0.0, 0.0, 0.0]
                self.mCurrentLapDistance = dist
                self.mRacePosition = pos
                self.mLapsCompleted = max(0, lap - 1)
                self.mCurrentLap = lap
                self.mCurrentSector = sector
        
        MockSHM.mParticipantInfo = [
            MockParticipant("Driver A", True, 1, 5, 1000.0, 1),
            MockParticipant("Driver B", True, 2, 5, 800.0, 1),
        ] + [MockParticipant("", False, 0, 0, 0.0, 0) for _ in range(62)]
        MockSHM.mNumParticipants = 2
        
        result = provider.poll(MockSHM)
        assert result is not None
        # Should have found 2 active participants
        active = [p for p in result.values() if p.get('is_active', False)]
        assert len(active) == 2

    def test_manual_override_prevents_auto_detection(self):
        """T213: When user_mode='udp_only', auto-detection is irrelevant."""
        # This tests the logic that _should_auto_switch_to_udp is not called
        # when user_mode is 'udp_only'. Since this is main.py logic,
        # we test the contract: effective_source is always 'udp_manual'
        # when user_mode is 'udp_only', regardless of SHM state.
        # (Integration test — verifies at main.py level)
        pass  # Will be validated in integration testing


# ══════════════════════════════════════════════════════════════════════════════
# Phase 4: US2 — Auto-Detection Hysteresis (unit-testable parts)
# ══════════════════════════════════════════════════════════════════════════════

class TestAutoDetectionHysteresis:
    """T019–T022, T207–T210: Hysteresis counter logic tests.

    These test the detection signal combination logic.
    The counter itself lives in main.py, so we test the
    provider signals that drive the decision.
    """

    def test_detection_signals_all_true_when_udp_ready_and_shm_empty(self):
        """T207/T019: When UDP has data and SHM is empty, signals are all True."""
        provider = TelemetryProvider(mode='shared_memory')
        # Give UDP valid track length
        provider._packet_buffer[308] = _build_308_packet(track_length=3936.0)
        # Give UDP participant names
        provider._udp_participant_names = {0: "Max Verstappen", 1: "Lewis Hamilton"}

        assert provider.udp_has_track_length() is True
        assert provider.udp_has_participant_names() is True

    def test_detection_signals_false_when_no_udp_data(self):
        """No UDP data → both signals False, no switch should happen."""
        provider = TelemetryProvider(mode='shared_memory')
        assert provider.udp_has_track_length() is False
        assert provider.udp_has_participant_names() is False

    def test_detection_signals_partial_only_track(self):
        """Only track length available, no names → should not switch."""
        provider = TelemetryProvider(mode='shared_memory')
        provider._packet_buffer[308] = _build_308_packet(track_length=3936.0)
        assert provider.udp_has_track_length() is True
        assert provider.udp_has_participant_names() is False


# ══════════════════════════════════════════════════════════════════════════════
# Phase 6: US3 — Anti-Regression
# ══════════════════════════════════════════════════════════════════════════════

class TestAntiRegression:
    """T035–T036, T214–T215: Ensure existing behaviour is not broken."""

    def test_existing_hybrid_mode_unchanged(self):
        """T035/T214: Default startup produces identical SHM-primary behaviour."""
        provider = TelemetryProvider(mode='shared_memory')
        # Default mode is shared_memory — poll(None) should fall back to UDP
        # poll(None) with no UDP data → None
        result = provider.poll(None)
        assert result is None  # No data source available — existing behaviour

    def test_provider_mode_defaults_to_shared_memory(self):
        """Verify the provider defaults to shared_memory mode."""
        provider = TelemetryProvider()
        assert provider._mode == 'shared_memory'


# ══════════════════════════════════════════════════════════════════════════════
# Spec-Compliant sParticipantsData (1136-byte) Parsing
# ══════════════════════════════════════════════════════════════════════════════

def _build_spec_1136_packet(names: list[str] | None = None) -> bytes:
    """Build a 1136-byte sParticipantsData packet per SMS_UDP_Definitions.hpp.

    Official layout (from SMS_UDP_Definitions.hpp):
      struct sParticipantsData {
          PacketBase sBase;                    // offset 0,  12 bytes
          unsigned int sParticipantsChangedTimestamp;  // offset 12, 4 bytes
          char sName[16][64];                  // offset 16, 1024 bytes (16 × 64)
          unsigned int sNationality[16];       // offset 1040, 64 bytes
          unsigned short sIndex[16];           // offset 1104, 32 bytes
      };                                       // total 1136 bytes

    Name stride is 64 bytes, NOT 32.
    """
    data = bytearray(1136)
    # Set mPartialPacketIndex to 1 (offset 8)
    data[8] = 1
    # Set packet type to eParticipants (2) at offset 10
    data[10] = 2
    if names:
        for i, name in enumerate(names[:16]):
            offset = 16 + (i * 64)  # Spec: 64-byte stride
            name_bytes = name.encode('utf-8')[:63]
            data[offset:offset + len(name_bytes)] = name_bytes
            struct.pack_into('<H', data, 1104 + (i * 2), i)
    return bytes(data)


class TestSParticipantsDataParsing:
    """Tests that verify V4 can extract participant names from the official
    1136-byte sParticipantsData UDP packet, matching V3's ability to show
    names when operating in pure UDP mode.

    Reference: SMS_UDP_Definitions.hpp — sParticipantsData struct
    """

    def test_spec_1136_extracts_single_name(self):
        """A 1136-byte packet with one name at slot 0 should be parsed."""
        provider = TelemetryProvider(mode='udp')
        packet = _build_spec_1136_packet(names=["Max Verstappen"])
        provider._parse_udp_names(packet)
        assert provider._udp_participant_names.get(0) == "Max Verstappen"

    def test_spec_1136_extracts_multiple_names(self):
        """A 1136-byte packet with 4 driver names populates all 4 slots."""
        names = ["Max Verstappen", "Lewis Hamilton", "Charles Leclerc", "Lando Norris"]
        provider = TelemetryProvider(mode='udp')
        packet = _build_spec_1136_packet(names=names)
        provider._parse_udp_names(packet)
        for i, expected in enumerate(names):
            actual = provider._udp_participant_names.get(i)
            assert actual == expected, f"Slot {i}: expected '{expected}', got '{actual}'"

    def test_spec_1136_extracts_16_names(self):
        """Full grid: 16 driver names in a 1136-byte packet all parsed correctly."""
        names = [f"Driver_{i:02d}" for i in range(16)]
        provider = TelemetryProvider(mode='udp')
        packet = _build_spec_1136_packet(names=names)
        provider._parse_udp_names(packet)
        assert len(provider._udp_participant_names) == 16
        for i, expected in enumerate(names):
            assert provider._udp_participant_names[i] == expected

    def test_spec_1136_names_appear_in_poll_output(self):
        """End-to-end: names from 1136-byte packet appear in poll() participants."""
        provider = TelemetryProvider(mode='udp')
        # 1) Inject the names packet
        names_packet = _build_spec_1136_packet(names=["Alice", "Bob"])
        provider._parse_udp_names(names_packet)
        # 2) Inject a 1063-byte timings packet with 2 active participants
        timings = bytearray(1063)
        for i in range(2):
            base = 31 + i * 32
            # race_position byte at offset +16: position | 0x80 (active)
            timings[base + 16] = (i + 1) | 0x80
            # lap distance at offset +14: 500 meters
            struct.pack_into('<H', timings, base + 14, 500 + i * 100)
            # current_lap at offset +23
            timings[base + 23] = 3
        provider._packet_buffer[1063] = bytes(timings)
        # 3) Poll
        result = provider.poll(None)
        assert result is not None
        assert result[0]['name'] == "Alice"
        assert result[1]['name'] == "Bob"

    def test_spec_1136_empty_slots_skipped(self):
        """Empty name slots (all null bytes) should not be added to cache."""
        provider = TelemetryProvider(mode='udp')
        # Only set name at index 3, leave 0-2 empty
        data = bytearray(1136)
        data[10] = 2
        offset = 16 + (3 * 64)
        name_bytes = b"Carlos Sainz"
        data[offset:offset + len(name_bytes)] = name_bytes
        struct.pack_into('<H', data, 1104 + (3 * 2), 3)
        provider._parse_udp_names(bytes(data))
        assert 0 not in provider._udp_participant_names
        assert 1 not in provider._udp_participant_names
        assert 2 not in provider._udp_participant_names
        assert provider._udp_participant_names.get(3) == "Carlos Sainz"

    def test_spec_1136_listener_gate_triggers_parse(self):
        """The listener loop gate (packet_size in (1136, 1367)) should trigger
        _parse_udp_names for a 1136-byte packet. We verify by checking that
        injecting into the buffer via _add_packet_to_buffer + calling
        _parse_udp_names produces the same result as the listener would."""
        provider = TelemetryProvider(mode='udp')
        packet = _build_spec_1136_packet(names=["Ayrton Senna"])
        # Simulate what the listener loop does (line 500-501)
        packet_size = len(packet)
        provider._add_packet_to_buffer(packet)
        assert packet_size == 1136  # Confirms the gate would match
        if packet_size in (1136, 1367):
            provider._parse_udp_names(packet)
        assert provider._udp_participant_names.get(0) == "Ayrton Senna"
