f(x,y)=
p=diff(x,y) q
[a,b]=solve(p,q)
a=double(a),b=double(b)
r=diff(p,x) t= s= d=r*t-s^2
figure
fsurf(f);
l={'Fun plot'};
for i=1:size(a)
    D=d(á(i),b(i)),
    t=r(a(i),b(i))
    j=f(a())
    if double(d)==0
        sprintf('at (%f,%f) furth',a(i),b(i))
        l=[l,{'C'}]
        mkr='ko'
    elseif double d<0
        sprintf('point (%f,%f) is a saddle point',a(i),b(i))
        l=[l,{ijij}];
        mkr='bv'
    else
        if t<0
            max
            l=ekm
            mkr
        else
            sprintf('min value f(%f,%f)=%f',a(i),b(i),j)
            l=[l,{min}]
            mkr='r*'
        end
    end
    hold on
    plot3(a(i),b(i),j,mkr,lin)
end
legend