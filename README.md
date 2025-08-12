```
dd if=/dev/zero of=data bs=1MiB count=100 status=progress
ampart data --mode ecreate
ampart data --mode eedit ^cache\?
dd if=data of=reserved bs=1MiB skip=36 count=64 status=progress

===================================================================================
ID| name            |          offset|(   human)|            size|(   human)| masks
-----------------------------------------------------------------------------------
 0: bootloader                      0 (   0.00B)           400000 (   4.00M)      0
 1: env                        400000 (   4.00M)           800000 (   8.00M)      0
    (GAP)                                                 1800000 (  24.00M)
 2: reserved                  2400000 (  36.00M)          4000000 (  64.00M)      0
===================================================================================
```
