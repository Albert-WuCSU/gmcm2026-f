"""Source-backed paper flowcharts with grouped branches and explicit dependencies."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
import numpy as np
import figstyle as S

INK = '#333333'
INPUT = '#E2E2E2'
METHOD = '#FAF6D9'
PROCESS = '#DCEBF1'
OUTPUT = '#DCEADC'
CHECK = '#F4DFD8'


def canvas(height=4.6):
    fig, ax = plt.subplots(figsize=(7.2, height))
    fig.subplots_adjust(left=.015, right=.985, bottom=.025, top=.975)
    ax.set(xlim=(0,100), ylim=(0,100))
    ax.axis('off')
    return fig, ax


def node(ax, x, y, w, h, title, body='', fill='white'):
    ax.add_patch(Rectangle((x,y),w,h,fc=fill,ec=INK,lw=.85,zorder=2))
    if body:
        ax.text(x+w/2,y+h*.68,title,ha='center',va='center',fontsize=9,
                weight='bold',color=INK,zorder=3)
        ax.text(x+w/2,y+h*.28,body,ha='center',va='center',fontsize=8,
                color=INK,linespacing=1.35,zorder=3)
    else:
        ax.text(x+w/2,y+h/2,title,ha='center',va='center',fontsize=9,
                color=INK,weight='bold',linespacing=1.45,zorder=3)


def group(ax,x,y,w,h,label,label_x=None):
    ax.add_patch(Rectangle((x,y),w,h,fc='#FAFAFA',ec=INK,lw=.75,
                           ls=(0,(5,3)),zorder=0))
    ax.text(x+1.5 if label_x is None else label_x,y+h,label,fontsize=8,weight='bold',va='center',ha='left',
            bbox=dict(fc='white',ec='none',pad=2),color=INK,zorder=4)


def edge(ax, points, label=None, label_at=None, dashed=False, head=True):
    points = [p for i,p in enumerate(points) if i == 0 or p != points[i-1]]
    # Draw to the exact box boundary. FancyArrowPatch shortens its endpoint
    # even after shrinking is disabled; explicit triangles avoid that gap.
    xs, ys = zip(*points)
    ax.plot(xs,ys,color=INK,lw=.85,ls=':' if dashed else '-',
            solid_capstyle='butt',solid_joinstyle='miter',zorder=1)
    if head:
        start, tip = ax.transData.transform(np.array(points[-2:]))
        delta = tip-start
        length = np.linalg.norm(delta)
        direction = delta/length
        normal = np.array([-direction[1],direction[0]])
        px_per_pt = ax.figure.dpi/72
        head_length = min(5.5*px_per_pt,length)
        half_width = 2.1*px_per_pt
        base = tip-direction*head_length
        vertices = ax.transData.inverted().transform(
            [tip,base+normal*half_width,base-normal*half_width])
        ax.add_patch(Polygon(vertices,closed=True,fc=INK,ec='none',zorder=2.5))
    if label:
        ax.text(*label_at,label,fontsize=7.5,ha='center',va='center',color=INK,
                zorder=4)


def split(ax, source, destinations, bus_y):
    """One stem, one crossbar, and separate arrowheads at destination boxes."""
    edge(ax, [source, (source[0], bus_y)], head=False)
    xs = [p[0] for p in destinations]
    edge(ax, [(min(xs), bus_y), (max(xs), bus_y)], head=False)
    for x, y in destinations:
        edge(ax, [(x, bus_y), (x, y)])


def merge(ax, sources, destination, bus_y):
    """Plain incoming lines join a crossbar; only the outgoing stem has a head."""
    for x, y in sources:
        edge(ax, [(x, y), (x, bus_y)], head=False)
    xs = [p[0] for p in sources]
    edge(ax, [(min(xs), bus_y), (max(xs), bus_y)], head=False)
    edge(ax, [(destination[0], bus_y), destination])


def q1():
    fig,ax=canvas()
    node(ax,34,87,32,11,'原始质量信号','20 列主口径',INPUT)
    edge(ax,[(50,87),(50,81)])
    node(ax,27,70,46,11,'方向统一与信号规范化','合并总体分位数 · 列表指标压缩',PROCESS)
    group(ax,4,45,92,19,'信号分组')
    node(ax,9,48,35,12,'14 项价值指标','$V$：价值合成',METHOD)
    node(ax,56,48,35,12,'6 项污染指标','$P$：污染合成',METHOD)
    split(ax,(50,70),[(26.5,60),(73.5,60)],67)
    node(ax,34,24,32,11,'门控质量合成','$Q=V(1-P)$',OUTPUT)
    merge(ax,[(26.5,48),(73.5,48)],(50,35),41)
    group(ax,4,2,41,20,'冲突识别')
    node(ax,8,5,33,13,'高价值且高污染','$\\mathrm{CD2}@p_{75}$',CHECK)
    edge(ax,[(26.5,41),(2,41),(2,11.5),(8,11.5)],'价值 / 污染',(11,32))
    group(ax,55,2,41,19,'配比检验',label_x=80)
    node(ax,59,5,33,13,'域级聚合与配比建模','Huber 聚合\n主效应 · 交互 · 岭回归',OUTPUT)
    edge(ax,[(50,24),(50,23),(75.5,23),(75.5,18)])
    return S.save(fig,'fig_framework_q1')


def q2():
    fig,ax=canvas(5.4)
    group(ax,2,80,96,19,'数据来源')
    node(ax,6,84,28,12,'B2 / B4 / B5','外部验证来源',INPUT)
    node(ax,36,84,28,12,'B1 真实训练轨迹','经典标度律参数',INPUT)
    node(ax,66,84,28,12,'B7 半合成质量网格','设计质量刻度',INPUT)
    node(ax,27,65,46,10,'广义标度律与退化检验','质量 · 配比进入有效数据量',METHOD)
    edge(ax,[(50,84),(50,75)])
    edge(ax,[(70,84),(70,75)])
    group(ax,2,38,96,20,'参数估计')
    node(ax,6,40,40,14,'主路线 A','B1 定 $\\beta$ · B7 定 $\\gamma$\n来源分层 WLS 联合核验',PROCESS)
    node(ax,54,40,40,14,'敏感性路线 B','B7 自由估计 $\\beta$、$\\gamma$\n与路线 A 对照',PROCESS)
    split(ax,(50,65),[(26,54),(74,54)],62)
    node(ax,6,21,40,13,'跨源验证','秩相关 · 去源偏 RMSE',CHECK)
    edge(ax,[(26,40),(26,34)])
    edge(ax,[(20,84),(20,79),(.5,79),(.5,27.5),(6,27.5)])
    node(ax,21,0,58,14,'条件化结果与适用边界','质量指数 · 边际效应 · 替代关系\n保留跨源共享假设的检验限制',OUTPUT)
    edge(ax,[(26,21),(26,14)])
    edge(ax,[(74,40),(74,14)])
    return S.save(fig,'fig_framework_q2')


def q3():
    fig,ax=canvas(4.6)
    node(ax,3,84,43,14,'目标与算力约束','固定配比，给定 $C$\n最小化损失 $L$',INPUT)
    node(ax,54,84,43,14,'质量成本函数 $g(Q)$','指数 · 幂函数 · 对数型',INPUT)
    node(ax,34,62,32,12,'分段 KKT 条件',fill=METHOD)
    merge(ax,[(24.5,84),(75.5,84)],(50,74),80)
    group(ax,3,35,94,21,'活跃集分支')
    for x,title,body in [(7,'质量下界分支','$Q^*=Q_0$'),(37,'内点分支','$Q_0<Q^*<1$'),(67,'质量上界分支','$Q^*=1$')]:
        node(ax,x,38,26,14,title,body,PROCESS)
    split(ax,(50,62),[(20,52),(50,52),(80,52)],59)
    node(ax,29,18,42,12,'可行性核验与候选解比较','选择最小损失的合法配置',OUTPUT)
    merge(ax,[(20,38),(50,38),(80,38)],(50,30),36)
    node(ax,3,0,43,10,'预算扫描与结构转移定位',fill=OUTPUT)
    node(ax,54,0,43,10,'成本形式与上下文敏感性',fill=CHECK)
    split(ax,(50,18),[(24.5,10),(75.5,10)],16)
    return S.save(fig,'fig_framework_q3')


def q4():
    fig,ax=canvas(5.2)
    node(ax,23,86,54,12,'C1 榜单与 C4 模型元数据','2024-06 至 2025-03',INPUT)
    group(ax,2,47,62,33,'主分解输入与规格')
    node(ax,6,62,54,13,'逐模型得分与参数量','C1 Average · C4 参数量',PROCESS)
    node(ax,6,50,54,9,'log N 十分位 + 月度固定效应',fill=METHOD)
    node(ax,70,64,27,11,'月度能力前沿','$S_{q90}$',PROCESS)
    split(ax,(50,86),[(33,75),(83.5,75)],83)
    edge(ax,[(33,62),(33,59)])
    node(ax,6,25,54,14,'能力变化的通道分解','规模贡献 + 非规模月度共同变动',OUTPUT)
    edge(ax,[(33,50),(33,39)])
    node(ax,70,44,22,12,'Q2 参数与桥接','Loss → 榜单分数',INPUT)
    node(ax,6,4,54,14,'端点与规格敏感性','基线对照 · 方向与量级',CHECK)
    edge(ax,[(33,25),(33,18)])
    node(ax,70,4,27,32,'前沿情景预测','归因份额 · 前沿趋势\n12 / 24 个月\n三情景 · 纯趋势基线',OUTPUT)
    edge(ax,[(60,32),(70,32)])
    edge(ax,[(95,64),(95,36)])
    edge(ax,[(81,44),(81,36)])
    return S.save(fig,'fig_framework_q4')


def overall():
    fig,ax=canvas(5.4)
    rows=[(76,'问题一','A 质量信号与配方实验','质量合成与冲突识别\n配比拟合与质量增量检验'),
          (52,'问题二','B 训练轨迹与质量网格','广义标度律与参数估计\n跨源验证与边际分析'),
          (28,'问题三','标度律参数与题给成本','算力约束下分段优化\n最优配置与结构转移'),
          (4,'问题四','C 榜单与模型元数据\nQ2 参数与 Loss 桥接','规模 / 非规模通道分解\n能力前沿与情景预测')]
    for y,title,inp,method in rows:
        group(ax,2,y,74,20,title)
        node(ax,5,y+4,29,12,inp,fill=INPUT)
        node(ax,40,y+3,32,14,method,fill=METHOD)
        edge(ax,[(34,y+10),(40,y+10)])
    edge(ax,[(56,79),(56,69)],'配比系数',(64,74))
    edge(ax,[(56,55),(56,45)],'标度律参数',(65,50))
    edge(ax,[(56,31),(56,21)],'配置规律',(65,26))
    group(ax,81,4,17,92,'共同检验')
    for y,t in [(74,'基线\n对照'),(52,'参数与口径\n敏感性'),(30,'条件性与\n外推边界'),(8,'证据与结论\n一致性')]:
        node(ax,83,y,13,16,t,fill=CHECK)
    for y in [86,62,38,14]: edge(ax,[(76,y),(81,y)])
    return S.save(fig,'fig_framework_overall')


def data_pipeline():
    p=S.load_json('workspace/data/data_profile.json')
    total=p['coverage']['rows']['A_quality_total']
    n=S.load_json('workspace/data/q1_canonical_verification.json')['n_rows']
    count=len(p['raw_files'])
    assert 0<n<=total
    print(f'[facts] 原始附件 {count} 个；Q1 主样本 {n:,}/{total:,}，剔除 {total-n} 行')
    fig,ax=canvas(4.4)
    node(ax,24,86,52,12,f'{count} 个原始附件','按问题映射，分别处理',INPUT)
    items=[(2,'Q1 质量','方向统一 · 列表压缩\n合并总体经验分位数',f'{n:,} 行主样本\n剔除 {total-n} 行缺失'),
           (35,'Q2 / Q3','数据来源分层\n参数量与 token 单位统一','标度律估计数据\n算力约束与成本参数'),
           (68,'Q4 榜单','名称连接 · 月度归组\n沿用 Average 与参数量','能力前沿与规模分布\n通道分解与情景输入')]
    for x,title,processing,out in items:
        group(ax,x,25,30,53,title)
        node(ax,x+2,56,26,16,processing,fill=PROCESS)
        node(ax,x+2,29,26,17,out,fill=OUTPUT)
        edge(ax,[(x+15,56),(x+15,46)])
    split(ax,(50,86),[(17,72),(50,72),(83,72)],82)
    node(ax,13,2,74,14,'可追溯的数据输入','保留来源与处理口径 · 原始附件不覆盖',fill=INPUT)
    merge(ax,[(17,29),(50,29),(83,29)],(50,16),21)
    return S.save(fig,'fig_data_pipeline')


def main():
    S.apply_style()
    out=overall()+data_pipeline()+q1()+q2()+q3()+q4()
    print('[figs]',*out,sep='\n  ')

if __name__=='__main__': main()
