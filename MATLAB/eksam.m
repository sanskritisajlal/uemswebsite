clear
clc
syms x y 
f(x,y)=input('');
div=divergence(f,[x,y])
p(x,y)=f(1);q(x,y)=f(2);
x=linspace(-4,4,20),y=x;
[X,Y]=meshgrid(x,y);
U=p(X,Y);V=q(X,Y);
figure
pcolor(X,Y,div(X,Y))
shading iterp
hold on;
quiver(X,Y,U,V,1)
title('Vector field')