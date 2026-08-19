def apply_ips(rom_bytes, ips_bytes):
    r=bytearray(rom_bytes); d=ips_bytes
    assert d[:5]==b'PATCH', 'IPS 아님'
    i=5
    while True:
        if d[i:i+3]==b'EOF': break
        off=int.from_bytes(d[i:i+3],'big'); i+=3
        ln=int.from_bytes(d[i:i+2],'big'); i+=2
        if ln==0:
            rl=int.from_bytes(d[i:i+2],'big'); i+=2
            b=d[i]; i+=1
            if off+rl>len(r): r.extend(b'\x00'*(off+rl-len(r)))
            r[off:off+rl]=bytes([b])*rl
        else:
            if off+ln>len(r): r.extend(b'\x00'*(off+ln-len(r)))
            r[off:off+ln]=d[i:i+ln]; i+=ln
    return bytes(r)
