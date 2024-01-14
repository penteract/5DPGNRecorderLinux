import sys
import pieces

#If the game gets updated, hopefully fixing this is as easy as rerunning 
#findboards.py (while playing a Standard game) and changing this to the offset printed there 
boardsPointerOffset = 0x4250

boardFields = ["boardId",
"timeline",
"turn",
"isBlacksMove",
"positionData128",
"moveNumber", #-1 until a move is made from this board. After a move is made, it becomes the number of moves made before that one.
"val05", #probably isn't an int - values seen: 1 257, 513, 1009807616 
"moveSourceL",
"moveSourceT",
"moveSourceIsBlack",
"moveSourceY",
"moveSourceX",
"moveDestL",
"moveDestT",
"moveDestIsBlack",
"moveDestY",
"moveDestX",
"creatingMoveNumber", # moveNumber of the move that created this board
"nextInTimelineBoardId",# The id of the next board in the same timeline as this one
"previousBoardId", # the id of the board that was before this board, or this board branches off after
"val19",
"ttPieceOriginId", # the board id where this piece came from, or -1 if no timetravel happened
"ttMoveSourceY", # source timetravel move y (on the board where the piece disappeared) if source x and y are -1 then the piece is appearing on this board, coming from somewhere else
"ttMoveSourceX", # source timetravel move X
"ttMoveDestY",  # dest timetravel move y (on the board where the piece appeared) if dest x and y are -1 then the piece is disappearing on this board, going to somewhere else
"ttMoveDestX"]

boardSize = 228
assert boardSize == (len(boardFields)-1)*4+128

def parse(mem,offset):
    d={}
    for k in boardFields:
        if k=="positionData128":
            offset+=128
            continue
        d[k] = int.from_bytes(mem[offset:offset+4], "little")
        print(k,d[k])
        offset+=4

if __name__=="__main__":
    with open(sys.argv[1],mode="rb") as f:
        f.seek(eval(sys.argv[2]))
        mem = f.read(228)
        d = parsemem(mem,0)
        for k in d:
            print(k,d[k])


DIoffsets = {
    "ChessArrayPointer" : 0,
    "ChessArraySize" : -8,
    "ChessBoardSizeWidth" : 0xA8 + 0x4,
    "ChessBoardSizeHeight" : 0xA8,
    "CurrentPlayersTurn" : 0x130,
    "GameEndedWinner" : 0xCC,
    "GameState" : 0xD0,
    "WhiteTime" : 0x1A8,
    "BlackTime" : 0x1AC,
    "WhiteIncrement" : 0x1B0,
    "BlackIncrement" : 0x1B4,
    "CosmeticTurnOffset" : -0x20,
    "EvenTimelines" : -0x34, # 0 if odd number of starting timelines, -1 if even
    "WhoAmI" : -0x610,
    "WhoAmI2" : -0x44,
    "Perspective" : -0x40,
    "CurrentMoveIndexForUndo":0x150 # decrementing this allows undoing submitted moves (in single player)
}
minOffset = min(DIoffsets.values())
maxOffset = max(DIoffsets.values())

def i32(bs,off=0):
    return int.from_bytes(bs[off:off+4],"little",signed=True)

class Board():
    def __init__(self,mem,offset,width,height):
        self.width=width
        self.height=height
        props = {}
        self.props=props
        for k in boardFields:
            if k=="positionData128":
                props[k] = mem[offset:offset+128]
                offset += 128
            else:
                props[k] = i32(mem,offset)
                offset+=4
            self.__dict__[k]=props[k]
    def toFEN(self,l,t):
        b = ""
        for y in range(self.height-1,-1,-1):
            if y<self.height-1: b += "/"
            for x in range(self.width):
                b+=self.getAtCase(x,y)
        for i in range(8,1,-1):
            b=b.replace(" "*i,str(i))
        return f"[{b}:{l}:{t}:{'w' if self.isBlacksMove else 'b'}]"
    def getAt(self,x,y):
        if x<0 or y<0 or x>7 or y>7:
            raise Exception("outside Board")
        return pieces.ps[self.positionData128[x*16+y*2]]
    def getAtCase(self,x,y):
        col = self.positionData128[x*16+y*2+1]
        if col==0:
            return " "
        elif col==1:
            return self.getAt(x,y)
        elif col==2:
            return self.getAt(x,y).lower()
        raise Exception(f"unexpected colour {col} (expected 0,1 or 2)")

class DI:
    def __init__(self, memfile, blockStart):
        self.memfile = memfile
        self.blockStart = blockStart
        self.reread()
    def getState(self):
        whoWon = self.GameEndedWinner
        gs = self.GameState
        if gs==0:
            if whoWon != -1: print(f"Unexpected Data - gs is 0(running) but winning player '{whoWon}' is not -1")
            return "Running"
        elif gs in {1,3,5}:
            if whoWon==0:
                return "EndedWhiteWon"
            elif whoWon==1:
                return "EndedBlackWon"
            else:
                return "Ended"
        elif gs==2:
            return "EndedDraw"
        else:
            return "Unknown"
    def curT(self):
        return (self.BlackTime+self.BlackIncrement
                  if self.CurrentPlayersTurn else
                self.WhiteTime+self.WhiteIncrement)
    def isOver(self):
        return self.getState().startswith("Ended")
    def reread(self):
        print(self.blockStart)
        self.memfile.seek(self.blockStart + boardsPointerOffset + minOffset)
        self.mem = self.memfile.read(maxOffset+8-minOffset)
        vals = {}
        for k in DIoffsets:
            off = DIoffsets[k]-minOffset
            if k.endswith("Pointer"):  
                vals[k] = int.from_bytes(self.mem[off:off+8],
                                  "little", signed=True)
            else:
                vals[k] = i32(self.mem,off)
            self.__dict__[k] = vals[k]
        self.props = vals
        self.memfile.seek(self.ChessArrayPointer)
        self.boardsMem = self.memfile.read(boardSize*self.ChessArraySize)
        boards = []
        offset = 0
        for i in range(self.ChessArraySize):
            #offset = i*boardSize
            boards.append(Board(self.boardsMem, i*boardSize, self.ChessBoardSizeWidth, self.ChessBoardSizeHeight))
        self.boards = boards

    def pr(self):
        for k in DIoffsets:
            print(k,self.__dict__[k])
