"""VBF (Ford/Volvo Binary Format) firmware container parser.

A VBF file is a text header (vbf_version, sw_part_number, etc.) closed by a
'}' line, followed by binary blocks:
    [4B start address][4B length][length bytes of data][2B checksum]

If your file is a raw .bin with a single known load address, use
blocks_from_raw() instead. Checksum algorithms vary between VBF revisions;
the stored checksum is reported but treated as informational.
"""


class VBFError(Exception):
    pass


class Block:
    __slots__ = ("address", "data", "checksum")

    def __init__(self, address, data, checksum=None):
        self.address, self.data, self.checksum = address, data, checksum

    def __len__(self):
        return len(self.data)


def parse_vbf(path):
    with open(path, "rb") as f:
        blob = f.read()
    end = blob.find(b"}")
    if end < 0:
        raise VBFError("No '}' header terminator found - not a VBF file?")
    header_raw = blob[:end].decode(errors="replace")
    header = {}
    for line in header_raw.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            header[k.strip()] = v.strip().strip(";").strip('"')
    body = blob[end + 1:]
    # skip any whitespace/newline between header and first block
    i = 0
    while i < len(body) and body[i:i + 1].isspace():
        i += 1
    blocks = []
    while i + 8 <= len(body):
        addr = int.from_bytes(body[i:i + 4], "big")
        size = int.from_bytes(body[i + 4:i + 8], "big")
        i += 8
        if size == 0 or i + size > len(body):
            break
        data = body[i:i + size]
        i += size
        cks = int.from_bytes(body[i:i + 2], "big") if i + 2 <= len(body) else None
        i += 2
        blocks.append(Block(addr, data, cks))
    if not blocks:
        raise VBFError("No data blocks found after header")
    return header, blocks


def blocks_from_raw(path, load_address):
    with open(path, "rb") as f:
        return {"source": path}, [Block(load_address, f.read())]


def summarize(blocks):
    total = sum(len(b) for b in blocks)
    lo = min(b.address for b in blocks)
    hi = max(b.address + len(b) for b in blocks)
    return f"{len(blocks)} block(s), {total:,} bytes, range 0x{lo:08X}-0x{hi:08X}"
