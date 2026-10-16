m=['Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec','Jan','Feb','Mar']
tot26=[136277,184226,179768,209336,282410,305234,350945,522238,221434,286219,314867,512071]
net26=[114576,155269,150553,175585,242375,267234,310171,467940,194334,251740,276379,453134]
gro26=[125437,169573,163008,193810,266353,294613,343599,569223,209337,262864,295987,482337]
new26=[634,772,712,918,1192,1157,935,1443,600,991,946,1515]
meta26=[3499,20105,27357,33822,36622,30692,35791,77014,33206,30793,26894,43398]
goog26=[14642,15340,15169,17329,17338,15108,13409,18758,14753,29659,27919,42445]
tot27=[505730,368927,410174,504551,519109,516158,313266]
net27=[446497,323632,361546,447168,460228,457522,274206]
gro27=[503747,371599,417529,541589,547949,533490,313208]
new27=[1538,1294,1438,2362,1578,1353,592]
meta27=[38929,44244,43619,53009,65490,67698,35249]
goog27=[37226,38758,35831,40096,40401,40278,24676]
# Oct 1-15 2025
oct15={'tot':144681,'net':127405,'gro':136799}
for k,a,b in [('tot',tot26,tot27),('net',net26,net27),('gro',gro26,gro27)]:
    ytd26=sum(a[:6])+oct15[k]; rem26=sum(a)-ytd26; ytd27=sum(b)
    g=ytd27/ytd26
    jas26=sum(a[3:6])/3; jas27=sum(b[3:6])/3
    runrate=ytd27+rem26/jas26*jas27
    print(k,'FY26',sum(a),'ytd26',ytd26,'rem26',rem26,'ytd27',ytd27,'g',round(g,2),
      'proj_sustain',round(ytd27+rem26*g),'proj_runrate',round(runrate),
      'need7.8x',round((7.8e6-ytd27)/rem26,2),'need8.4x',round((8.4e6-ytd27)/rem26,2))
    print('  yoy by month',[round(b[i]/a[i],2) for i in range(6)], 'octMTD',round(b[6]/oct15[k],2))
def q(sp,nc,idx): return sum(sp[i] for i in idx)/sum(nc[i] for i in idx)
sp26=[x+y for x,y in zip(meta26,goog26)]; sp27=[x+y for x,y in zip(meta27,goog27)]
for name,sp,nc,qs in [('FY26',sp26,new26,[(0,1,2),(3,4,5),(6,7,8),(9,10,11)]),('FY27',sp27,new27,[(0,1,2),(3,4,5),(6,)])]:
    print(name,'CAC by Q',[round(q(sp,nc,i),1) for i in qs],'spend by Q',[sum(sp[j] for j in i) for i in qs])
print('monthly CAC 27',[round(s/n,1) for s,n in zip(sp27,new27)])
print('monthly CAC 26',[round(s/n,1) for s,n in zip(sp26,new26)])
print('YTD spend',sum(sp27),'new',sum(new27),'CAC',sum(sp27)/sum(new27))
print('MER ytd tot/spend',sum(tot27)/sum(sp27),'FY26',sum(tot26)/sum(sp26))
print('disc rate 26',[round(-1*0+ (g-n)/g,3) for g,n in zip(gro26,net26)])
