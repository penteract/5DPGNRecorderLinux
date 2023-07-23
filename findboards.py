#! /usr/bin/env python3
import subprocess
import re

import pieces

res = subprocess.run("ps -A | grep 5dchess", capture_output=True, shell=True)
assert res.returncode==0
s = str(res.stdout,encoding="ascii").split()
assert len(s)>0

def get_mem(pid):
    result = {}
    names = {}
    with open("/proc/"+pid+"/maps",mode="rb") as mapsfile:
        with open("/proc/"+pid+"/mem",mode="rb") as memfile:
            for l in mapsfile.readlines():
                m = re.match(rb'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([^ ]+) ([0-9A-Fa-f]+) ([0-9A-Fa-f]+:[0-9A-Fa-f]+) ([^ ]+) +([^ ]+)', l)
                #print(m.group(3),m.group(1),m.group(2),m.group(7))
                name = str(m.group(7),encoding="ascii")
                if b"r" not in m.group(3) or name.startswith("/usr/"):
                    continue
                start = int(m.group(1),16)
                end = int(m.group(2),16)

                try:
                    memfile.seek(start)
                    #print(hex(end-start),start,end)
                    result[start] = memfile.read(end-start)
                    names[start] = name
                except OSError:
                    if name!="[vvar]\n":
                        print("unable to read", name)
    return result,names


mem,nms = get_mem(s[0])

def search(target):
    result = []
    for k in mem:
        for res in re.finditer(target,mem[k]):
            result.append((k,res))
    return result

def counts(l):
    from collections import defaultdict
    d = defaultdict(int)
    for k in l:
        d[k]+=1
    return d

# find something that looks like a chessboard:
boards = search(b"\x04\x01([\x00-\x06][\x00-\x02]){62}\x04\x02")

print(len(boards))
prev = None
for k in boards:
    offset = k[0]+k[1].start()
    if prev is None or offset-prev!=228:
        if prev is not None:
            print("\ndelta",offset-prev)
        print(nms[k[0]][:-1],hex(offset), f"({hex(k[0])}+{hex(k[1].start())})")
        
    print(pieces.prg(k[1].group(0),"/"))
    prev = offset

#
addr = boards[0][0]+boards[0][1].start()-16
print("offset address of chessboard array", hex(addr))
addrAsBytes = (addr).to_bytes(8,"little")

ptrs = search(re.escape(addrAsBytes))
print("number of pointers to chessboard array found:",len(ptrs))
print("offset of first pointer (should match boardsPointerOffset in memlayout.py)", hex(ptrs[0][1].start()))
#print("block of first pointer",hex(ptrs[0][0]))

#cs = counts((x[1].group(0).count(b"\x00"),x[1].group(0).count(b"\x01")) for x in r)
#for k in sorted(cs):
#   print(k,cs[k])


