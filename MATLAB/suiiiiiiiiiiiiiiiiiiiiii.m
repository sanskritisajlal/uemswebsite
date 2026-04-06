clear
clc
syms x y z 
f=input('');
p(x,y)=f(1);q(x,y)=f(2);r(x,y)=f(3);
crl=curl(f,[x,y,z])
c1(x,y,z)=crl(1);c2(x,y,z)=crl(2);c3=crl(x,y,z);
x=linspace(-4,4,10);y=x;z=x;
[X,Y,Z]=meshgrid(x,y,z);
U=p(X,Y,Z);V=q(X,Y,Z);W=r(X,Y,Z);
CR1=c1(X,Y,Z);CR2=c2(X,Y,Z);CR3=c3(X,Y,Z);
figure;
subplot(1,2,1)
quiver3(X,Y,Z,U,V,W,1)
title('vector 3d field')
subplot(1,2,2)
quiver3(X,Y,Z,CR1,CR2,CR3)
title('curl')