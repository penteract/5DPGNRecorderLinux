
pieces = [
    "Empty"
  , "Pawn"
  , "kNight"
  , "Bishop"
  , "Rook"
  , "Queen"
  , "King"
  , "Unicorn"
  , "Dragon"
  , "Also unknown"
  , "braWn"
  , "princeSs"
  , "roYal queen"
  , "Commoner"
]
ps = "".join([c for c in s if c == c.upper()][0] for s in pieces )

#ps = " PNBRQK"

def prg(brd,split="\n"):
    b = brd[::2]
    s=""
    for x in range(8):
        for y in range(8):
            if x*8+y < len(b) and b[x*8+y] < len(ps):
                s+=ps[b[x*8+y]]
            else:
                s+="*"
        s+=split
    return (s)
