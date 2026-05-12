import ctypes
import json

def struct_to_dict(obj):
    """
    Recursively converts a ctypes.Structure or ctypes.Array into a standard
    Python dictionary suitable for JSON serialization.
    """
    # If the object is a primitive type (int, float, bool)
    if isinstance(obj, (int, float, bool)):
        return obj
    
    # If the object is bytes, decode to string
    if isinstance(obj, bytes):
        return obj.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
    
    # If the object is a ctypes string/char array
    if hasattr(obj, 'value') and isinstance(getattr(obj, 'value'), bytes):
        return getattr(obj, 'value').split(b'\x00')[0].decode('utf-8', errors='replace').strip()

    # If the object is an array
    if isinstance(obj, ctypes.Array):
        return [struct_to_dict(obj[i]) for i in range(len(obj))]

    # If the object is a structure
    if isinstance(obj, ctypes.Structure) or hasattr(obj, '_fields_'):
        result = {}
        for field_name, field_type in obj._fields_:
            # Extract the raw value from the structure
            try:
                val = getattr(obj, field_name)
            except AttributeError:
                continue
                
            # C-strings are automatically converted to bytes/str by ctypes
            if isinstance(val, bytes):
                result[field_name] = val.split(b'\x00')[0].decode('utf-8', errors='replace').strip()
            else:
                result[field_name] = struct_to_dict(val)
                
        return result
        
    # Catch-all for basic types like strings
    return str(obj)

def dump_struct_to_file(obj, filepath: str):
    """Safely dumps a ctypes struct to a JSON file."""
    try:
        data = struct_to_dict(obj)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"[TelemetryDumper] Error dumping struct to {filepath}: {e}")
        return False
