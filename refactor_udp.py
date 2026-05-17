import re

with open('core/telemetry_provider.py', 'r', encoding='utf-8') as f:
    content = f.read()

dict_match = re.search(r'UDP_NATIONALITY_HASHES = \{.*?\n\}', content, re.DOTALL)
dict_str = dict_match.group(0)
content = content.replace(dict_str, '')

udp_start = content.find('    def start_udp(self):')
udp_end = content.find('    def get_debug_dump_shm(self) -> dict:')
udp_methods = content[udp_start:udp_end]
content = content[:udp_start] + content[udp_end:]

content = content.replace("curr_participants = track_info.get('num_participants', 0)", "curr_participants = len(participants) if participants else 0")

content = content.replace('from core.physics_flywheel import PhysicsFlywheel', 'from core.physics_flywheel import PhysicsFlywheel\nfrom core.udp_parser import UDPParserMixin')
content = content.replace('class TelemetryProvider:', 'class TelemetryProvider(UDPParserMixin):')

with open('core/telemetry_provider.py', 'w', encoding='utf-8') as f:
    f.write(content)

with open('core/udp_parser.py', 'w', encoding='utf-8') as f:
    f.write('\"\"\"UDP parser mixin for TelemetryProvider.\"\"\"\n')
    f.write('import socket\nimport threading\nimport struct\nimport time\n\n')
    f.write(dict_str)
    f.write('\n\nclass UDPParserMixin:\n')
    # write as is, it already has 4 spaces!
    f.write(udp_methods)
