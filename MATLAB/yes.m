clear 
clc
syms x y z real
v=int(int(int(x^2+y^2+z^2,z,-sqrt(16-x^2-y^2),sqrt(16-x^2-y^2)),x,-sqrt(16-y^2),sqrt(16-y^2)),y,-4,4)