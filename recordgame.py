#! /usr/bin/env python3
import subprocess
import re
import sys
import time
import datetime
import os

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
        blockstart = int(m.group(1),16)
        blockend = int(m.group(2),16)
        print(f"Found memory block {hex(blockstart)}-{hex(blockend)}")
        assert blockend-blockstart == 24<<10
    memfile = open("/proc/"+pid+"/mem",mode="rb")
    return (memfile,blockstart)

def save(pgn):
    fname = datetime.datetime.now().strftime("5dpgn%Y%m%d_%H%M%S.txt")
    with open(fname,mode="w") as f:
        f.write(pgn)
        print("output saved to",fname)
def pgnEscape(s):
    return "".join(map((lambda c:"\\"+c if c in '\\"' else c),s))

class GameRecorder(memlayout.DI):
    def makePGN(self,playerName=None):
        def mkL(l):
            if self.EvenTimelines==0:
                return str(l)
            elif l>=0:
                return f"+{l}"
            elif l==-1:
                return "-0"
            else:
                return str(l+1)
        mkT = lambda t : str(t+self.CosmeticTurnOffset)
        mkLT = lambda l,t: f"({mkL(l)}T{mkT(t)})"
        now = datetime.datetime.now(datetime.timezone.utc).astimezone()
        tz = now.strftime("%z")
        tags = {
            "Mode" : "5D"
          , "Result" : self.resultString()
          , "Date" : now.strftime("%Y.%m.%d")
          , "Time" : now.strftime(f"%H:%M:%S ({tz[:-2]}:{tz[-2:]})")
          , "Size" : f"{self.ChessBoardSizeWidth}x{self.ChessBoardSizeHeight}"
          , "White" : None
          , "Black" : None
          , "Board" : "Custom"
        }
        if self.WhoAmI2==1:
            tags["White"] = "Opponent"
            if playerName is not None: tags["Black"] = playerName
        elif self.WhoAmI2==0:
            if playerName is not None: tags["White"] = playerName
            tags["Black"] = "Opponent"
        pgn = "\n".join(f'[{k} "{pgnEscape(v)}"]' for k,v in tags.items() if v is not None)
        lastCol = ""
        turnNumber = 0
        for i,b1 in enumerate(self.boards):
            assert i == b1.boardId
            if b1.previousBoardId==-1:
                pgn+="\n"+b1.toFEN(mkL(b1.timeline),mkT(b1.turn))
                continue
            b = self.boards[b1.previousBoardId]
            if (all( b.props["move"+k+c]<=0 for k in ["Source","Dest"] for c in "LTXY")
              and b.moveNumber in {b1.creatingMoveNumber,-1}):
                pgn+="\n"+b1.toFEN(mkL(b1.timeline),mkT(b1.turn))
                continue
            c = "b" if b.isBlacksMove else "w"
            if c!=lastCol:
                lastCol = c
                if c=="b":
                    pgn+="/ "
                else:
                    turnNumber+=1
                    #if turnNumber==1:
                        #pgn+=fen
                    pgn+=f"\n{turnNumber}."
            moveType = ""
            if i+1<len(self.boards):
                b2 = self.boards[i+1]
                if b2.creatingMoveNumber == b1.creatingMoveNumber:
                    moveType = ">" if b2.timeline==b.moveDestL else ">>"
            piece = b.positionData128
            src = (mkLT(b.moveSourceL,b.moveSourceT)+b.getAt(b.moveSourceX,b.moveSourceY)
              + chr(97+b.moveSourceX)+str(b.moveSourceY+1))
            dest = mkLT(b.moveDestL,b.moveDestT)+chr(97+b.moveDestX)+str(b.moveDestY+1)
            pgn += src+moveType+dest+" "
        return pgn
    def resultString(self):
        r = self.getState()
        if r=="NotStarted": return "NotStarted"
        elif r=="Running": return "*"
        elif r=="EndedDraw": return "1/2-1/2"
        elif r=="EndedWhiteWon": return "1-0"
        elif r=="EndedBlackWon": return "0-1"
        else: return "error"
    def getHash(self):
        """return a collection of data that should change if anything happens"""
        return (self.ChessArraySize,self.CurrentPlayersTurn,self.GameState)


usage = """python3 recordgame.py [-h] [--help] [NAME]

Find a running 5D chess with multiverse timetravel game and build PGN as
games are played. PGNs will be saved automatically when games finish.
NAME lets the program record which player is you as part of the PGN.

The Time tag includes the offset of your timezone from UTC, so if you consider
that information confidential, don't share the PGN without editing or removing
it."""

if __name__=="__main__":
    if any(x in sys.argv[1:] for x in ["-h","--help"]):
        print(usage)
        exit()
    res = subprocess.run("ps -A | grep 5dchess", capture_output=True, shell=True)
    assert res.returncode==0
    s = str(res.stdout,encoding="ascii")
    if s.count("\n") == 0:
        raise Exception("Can't find any 5D chess processes")
    if s.count("\n") > 1:
        raise Exception("More than 1 5D chess process")
    pid = s.split()[0]
    print("found process with id",pid)
    gr = GameRecorder(*get_mem(pid))

    #main loop:
    prevNumBoards = 0
    saved = False
    lastPGN=""
    lastHash=None
    playerName = os.environ.get("CHESSNAME")
    lastP = None
    try:
        while True:
            gr.reread()
            numBoards = gr.ChessArraySize
            if numBoards>0:
                changes = gr.getHash()
                if changes!=lastHash:
                    lastHash=changes
                    pgn = gr.makePGN(playerName=playerName)
                    if pgn != lastPGN: print("\n"+pgn)
                    lastPGN=pgn
                    if gr.isOver() and not saved:
                        save(pgn)
                        saved=True
                curTime = gr.curT()
                if gr.CurrentPlayersTurn!=lastP:
                    lastP=gr.CurrentPlayersTurn
                    lastTime = curTime
                if (curTime-1)*3<=(lastTime-1)*2:
                    os.system("aplay Tick.wav &")
                    lastTime = curTime
            else:
                if not saved and prevNumBoards>4:
                    save(pgn)
                if prevNumBoards>0:
                    print("\nNo chessboards")
                saved = False
                lastPGN = ""
            prevNumBoards = numBoards
            for k in []:#["WhoAmI","WhoAmI2", "GameState"]:
                print(k,gr.props[k])
            time.sleep(1)
    except BaseException as e:
        if lastPGN and not saved and prevNumBoards>0:
            print("emergency save")
            save(lastPGN)
        raise e

    #di.pr()
    #print(di.boards[0].props)
