#! /usr/bin/env python3
import subprocess
import re
import sys
import time
import datetime

import memlayout


def get_mem(pid):
    """Get memory file and location of "the right" block of memory"""
    result = {}
    names = {}
    with open("/proc/"+pid+"/maps",mode="rb") as mapsfile:
        for l in mapsfile.readlines():
            m = re.match(rb'([0-9A-Fa-f]+)-([0-9A-Fa-f]+) ([^ ]+) ([0-9A-Fa-f]+) (..:..) ([^ ]+) +([^ ]+)', l)
            if m.group(5)==b"00:00" and m.group(7)==b"\n":
                #print(m.group(0).decode("ascii"))
                break
        else:
            raise Exception("Can't find memory block")
        start = int(m.group(1),16)
        end = int(m.group(2),16)
        print(hex(start),hex(end))
        assert end-start == 24<<10
    memfile = open("/proc/"+pid+"/mem",mode="rb")
    return (memfile,start)

def save(pgn):
    fname = datetime.datetime.now().strftime("5dpgn%Y%m%d_%H%M%S.txt")
    with open(fname,mode="w") as f:
        f.write(pgn)
        print("output saved to",fname)

if __name__=="__main__":
    res = subprocess.run("ps -A | grep 5dchess", capture_output=True, shell=True)
    assert res.returncode==0
    s = str(res.stdout,encoding="ascii")
    if s.count("\n")==0:
        raise Exception("Can't find any 5D chess processes")
    if s.count("\n")>1:
        raise Exception("More than 1 5D chess process")
    pid = s.split()[0]
    print("found process with id",pid)
    di = memlayout.DI(*get_mem(pid))

    #main loop:
    prevNumBoards = 0
    saved = False
    lastPGN=""
    while True:
        time.sleep(1)
        di.reread()
        numBoards = di.ChessArraySize
        if numBoards>0:
            pgn = di.makePGN()
            if pgn != lastPGN: print(pgn)
            lastPGN=pgn
            if di.isOver() and not saved:
                save(pgn)
                saved=True
        else:
            if not saved and prevNumBoards>4:
                save(pgn)
            print("No chessboards")
            saved=False
        prevNumBoards = numBoards
    #di.pr()
    #print(di.boards[0].props)
