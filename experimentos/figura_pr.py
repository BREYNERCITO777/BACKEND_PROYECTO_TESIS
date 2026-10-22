"""Figura 11 del articulo: curvas precision-recall de v5 con los puntos de
operacion de la Tabla 7. Lee las curvas exportadas de la validacion de
Ultralytics (docs/evidencia_externa/v5/curvas_pr_v5.json).

Uso: python figura_pr.py  (desde la raiz del repositorio)
"""
import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
d=json.load(open("docs/evidencia_externa/v5/curvas_pr_v5.json"))
x=np.array(d["pr_x"]); y=np.array(d["pr_y"]); cx=np.array(d["conf_x"]); P=np.array(d["p_conf"]); R=np.array(d["r_conf"])
fig,ax=plt.subplots(figsize=(6.2,4.6),dpi=250)
ax.plot(x,y[0],color="#1f77b4",lw=1.3,label=f"Firearm (AP@0.5 {d['ap50'][0]:.3f})")
ax.plot(x,y[1],color="#ff7f0e",lw=1.3,label=f"Bladed weapon (AP@0.5 {d['ap50'][1]:.3f})")
ax.plot(x,y.mean(0),color="#222",lw=2.4,label=f"Both classes (mAP@0.5 {d['map50']:.3f})")
for c,lab,pos in [(0.70,"0.70",(0.30,0.80)),(0.65,"0.65 (default)",(0.42,0.68)),(0.50,"0.50",(0.56,0.56))]:
    i=np.abs(cx-c).argmin(); p,r=P[:,i].mean(),R[:,i].mean()
    ax.plot(r,p,"o",color="#c0392b",ms=6,zorder=5)
    ax.annotate(f"conf {lab}: P {p:.2f}, R {r:.2f}",(r,p),pos,fontsize=7.5,
                arrowprops=dict(arrowstyle="-",color="#c0392b",lw=0.8))
ax.set_xlim(0,1); ax.set_ylim(0,1.02); ax.set_xlabel("Recall"); ax.set_ylabel("Precision")
ax.grid(alpha=0.25); ax.legend(loc="lower left",fontsize=8,frameon=False)
fig.tight_layout(); fig.savefig("docs/evidencia_externa/v5/curva_pr_puntos_operacion.png")
