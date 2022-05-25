5DPGN recorder for Linux

Use `python3 recordgame.py` while the official client is running to display the moves.

`findboards.py` may help find the pointer again if there's an update. It should be run while playing a game with the standard layout (it looks for rooks in each corner of an 8*8 board)
(in the best case scenario, this might be fixed by changing the constant `boardsPointerOffset`
 in `memlayout.py` to the last number printed by `findboards.py` (currently 0x4250))

Credit to GHXX for initially reverse engineering the Windows version.
