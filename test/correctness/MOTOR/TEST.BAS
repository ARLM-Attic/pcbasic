10 REM PC-BASIC test 
20 REM MOTOR syntax
30 OPEN "OUTPUT.TXT" FOR OUTPUT AS 1
40 ON ERROR GOTO 1000
50 MOTOR
60 MOTOR PRINT
70 MOTOR LAH
80 MOTOR -1
90 MOTOR 0
100 MOTOR 255
110 MOTOR 256
120 MOTOR 32768
130 MOTOR "!"
140 MOTOR 1,1
150 MOTOR 1,
160 END
1000 PRINT#1, ERR, ERL
1010 RESUME NEXT
