10 REM PC-BASIC test 
20 REM WRITE syntax
30 OPEN "OUTPUT.TXT" FOR OUTPUT AS 1
40 ON ERROR GOTO 10000
50 WRITE
60 WRITE,
70 WRITE 1
80 WRITE 1,
90 WRITE ,1
100 WRITE 1, A%
110 WRITE PRINT
120 WRITE 1 PRINT
130 WRITE 1, PRINT
150 WRITE#1
160 WRITE#1,
170 WRITE#1  1
180 WRITE#1  1,
190 WRITE#1 ,1
210 WRITE#1 PRINT
220 WRITE#1, PRINT
230 WRITE#1, 1, PRINT
240 WRITE #1, 1, A%, 1#, "One"
9999 END
10000 PRINT#1, ERR, ERL
10010 RESUME NEXT
