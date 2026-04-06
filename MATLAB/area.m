clear all
clc
syms x
f(x)=x^3+12*x-5;
I=[-4,4];
f1(x)=-f(x);
a=I(1);b=I(2);
t=linspace(a,b,10000);
g=double(f(t));
[lmax_f,loc]=findpeaks(g);
maximum=round(t(loc),4);
h=double(f1(t));
[min,loc]=findpeaks(h);
minimum=round(t(loc),4);
disp('Local maximum:')
disp(maximum)
disp('Func value:')
disp(double(f(maximum)))