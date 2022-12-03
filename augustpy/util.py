

def _simple_checksum(buf: bytes):
    cs = 0
    for i in range(0x12):
        cs = (cs + buf[i]) & 0xFF

    return (-cs) & 0xFF


def _security_checksum(buffer: bytes):
    val1 = int.from_bytes(buffer[0x00:0x04], byteorder='little', signed=False)
    val2 = int.from_bytes(buffer[0x04:0x08], byteorder='little', signed=False)
    val3 = int.from_bytes(buffer[0x08:0x12], byteorder='little', signed=False)

    return (0 - (val1 + val2 + val3)) & 0xffffffff


def _copy(dest: bytearray, src: bytes, destLocation=0):
    dest[destLocation:(destLocation + len(src))] = src