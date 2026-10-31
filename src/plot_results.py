"""Editable Matplotlib figures bound to executed SQL tables."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np, pandas as pd

ROOT=Path(__file__).resolve().parents[1]
BLUE='#285D92'; ORANGE='#C57933'; GRAY='#6B7280'

def style():
    # Find a locally installed Chinese font. Portable fallback keeps Latin text readable.
    candidates=[Path('/System/Library/Fonts/STHeiti Light.ttc'),Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
    for path in candidates:
        if path.exists():
            font_manager.fontManager.addfont(str(path))
            plt.rcParams['font.family']=font_manager.FontProperties(fname=str(path)).get_name()
            break
    plt.rcParams.update({'font.size':11,'axes.titlesize':15,'axes.labelsize':11,
       'axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,
       'figure.facecolor':'white','axes.facecolor':'white','savefig.facecolor':'white'})

def table(name): return pd.read_csv(ROOT/f'results/tables/{name}.csv')

def funnel():
    frame=table('02_funnel')
    fig,ax=plt.subplots(figsize=(9.5,4.6))
    labels=['浏览','浏览后加购','加购后购买']
    ax.barh(labels[::-1],frame.visitors.values[::-1]/1e6,color=BLUE,height=.55)
    for y,row in enumerate(frame.iloc[::-1].itertuples()):
        ax.text(row.visitors/1e6+.025,y,f'{row.visitors:,} 人  |  {row.overall_conversion_pct:.2f}%',va='center',fontsize=11)
    ax.set_xlim(0,1.95);ax.set_xlabel('去重访客数（百万）');ax.set_title('大多数浏览访客未进入加购阶段',loc='left',pad=18)
    ax.grid(axis='x',color='#E5E7EB');ax.set_axisbelow(True)
    fig.text(.08,.03,'2015-05-03 至 09-18 UTC · 全观察期访客级 · 严格时间顺序 · 可跨商品和会话',fontsize=9,color=GRAY)
    fig.subplots_adjust(left=.17,right=.96,bottom=.20,top=.84)
    return fig

def sessions():
    frame=table('04_sessions')
    fig,ax=plt.subplots(figsize=(9.5,4.5))
    vals=frame.ordered_conversion_pct.to_numpy()
    bars=ax.bar(['首次观察会话','后续会话'],vals,color=[BLUE,ORANGE],width=.5)
    for b,row in zip(bars,frame.itertuples()):
        ax.text(b.get_x()+b.get_width()/2,b.get_height()+.055,f'{row.ordered_conversion_pct:.2f}%\n{row.ordered_buy_sessions:,} / {row.viewing_sessions:,}',ha='center',fontsize=11)
    ax.set_ylim(0,1.8);ax.set_ylabel('浏览后按序购买的会话比例（%）');ax.set_title('后续会话转化较高 但组间差异不能解释原因',loc='left',pad=18)
    ax.grid(axis='y',color='#E5E7EB');ax.set_axisbelow(True)
    fig.text(.08,.03,'按 30 分钟间隔划分会话 · 分母为含浏览的会话 · 同一访客可有多个后续会话',fontsize=9,color=GRAY)
    fig.subplots_adjust(left=.12,right=.97,bottom=.18,top=.83)
    return fig

def retention():
    frame=table('05_retention')
    grid=frame.pivot(index='cohort_week',columns='week_age',values='retention_pct').loc[:,1:8]
    fig,ax=plt.subplots(figsize=(10,8.4))
    cmap=plt.get_cmap('Blues').copy();cmap.set_bad('#EEEEEE')
    im=ax.imshow(np.ma.masked_invalid(grid.to_numpy()),cmap=cmap,vmin=0,vmax=6,aspect='auto')
    ax.set_xticks(range(len(grid.columns)),[str(x) for x in grid.columns]);ax.set_xlabel('首次观察周之后的第几周')
    ax.set_yticks(range(len(grid)),[x[5:] for x in grid.index]);ax.set_ylabel('首次观察活动所在周（2015 年）')
    for y in range(len(grid)):
        for x in range(len(grid.columns)):
            v=grid.iloc[y,x]
            ax.text(x,y,'—' if pd.isna(v) else f'{v:.1f}',ha='center',va='center',fontsize=9,color='white' if pd.notna(v) and v>3.5 else '#1F2937')
    ax.set_title('次周活动留存较低 后续周持续减少',loc='left',pad=16)
    fig.colorbar(im,ax=ax,pad=.02,label='活动留存（%）',shrink=.7)
    fig.text(.1,.02,'仅完整首次观察周和完整随访周 · 灰色表示观察不足 · 各单元格分母为该队列访客数',fontsize=9,color=GRAY)
    fig.subplots_adjust(left=.15,right=.94,bottom=.12,top=.91)
    return fig

def products():
    frame=table('07_products').head(8).iloc[::-1]
    fig,axes=plt.subplots(1,2,figsize=(10,5),gridspec_kw={'width_ratios':[1.35,1]})
    y=np.arange(len(frame));labels=frame.item_id.astype(str)
    axes[0].barh(y,frame.viewing_visitors,color=BLUE,height=.55)
    axes[0].set_yticks(y,labels);axes[0].set_xlabel('去重浏览访客数');axes[0].set_ylabel('商品匿名 ID')
    axes[0].set_xlim(0,3600)
    for i,v in enumerate(frame.viewing_visitors):axes[0].text(v+45,i,f'{v:,}',va='center',fontsize=10)
    axes[1].barh(y,frame.ordered_conversion_pct,color=ORANGE,height=.55)
    axes[1].set_yticks(y,[]);axes[1].set_xlabel('同商品按序购买比例（%）');axes[1].set_xlim(0,11)
    for i,v in enumerate(frame.ordered_conversion_pct):axes[1].text(v+.2,i,f'{v:.2f}%',va='center',fontsize=10)
    for ax in axes:ax.grid(axis='x',color='#E5E7EB');ax.set_axisbelow(True)
    fig.suptitle('高浏览量商品的转化差异值得进一步调查',x=.08,ha='left',fontsize=15)
    fig.text(.08,.025,'按浏览访客数选前 8 个商品 · 分母为各商品浏览访客 · 没有加购路径不代表没有直接购买',fontsize=9,color=GRAY)
    fig.subplots_adjust(left=.13,right=.96,bottom=.18,top=.88,wspace=.22)
    return fig

def metric_tree():
    r=table('10_metric_tree').iloc[0]
    fig,ax=plt.subplots(figsize=(14,7)); ax.set_axis_off()
    def box(x,y,text,color=BLUE):
        ax.text(x,y,text,ha='center',va='center',fontsize=10.5,
            bbox=dict(boxstyle='round,pad=.6',facecolor='#F2F6FA',edgecolor=color),transform=ax.transAxes)
    def link(x1,y1,x2,y2):
        ax.annotate('',xy=(x2,y2),xytext=(x1,y1),xycoords='axes fraction',
            arrowprops=dict(arrowstyle='-',color='#9AA5B1',lw=1.3))
    box(.5,.92,f'订单数  {int(r.orders):,} 单\n去重交易 ID')
    box(.25,.72,f'购买访客  {int(r.buyers):,} 人')
    box(.75,.72,f'人均订单  {r.orders_per_buyer:.3f} 单 / 人')
    box(.13,.49,f'严格顺序购买  {int(r.strict_buyers):,} 人\n{int(r.viewers):,} 浏览 × {r.cart_rate:.2%} × {r.purchase_rate:.2%}')
    box(.42,.49,f'其他购买路径  {int(r.other_buyers):,} 人\n购买访客 − 严格路径',ORANGE)
    box(.70,.49,f'单次购买者  {int(r.single_buyers):,} 人\n{int(r.single_buyers):,} 单')
    box(.90,.49,f'复购者  {int(r.repeat_buyers):,} 人\n{int(r.repeat_orders):,} 单',ORANGE)
    for line in [(.5,.86,.25,.78),(.5,.86,.75,.78),(.25,.66,.13,.56),(.25,.66,.42,.56),(.75,.66,.70,.56),(.75,.66,.90,.56)]:link(*line)
    ax.text(.5,.26,'购买访客 = 严格路径 + 其他路径     |     人均订单 =（单次购买订单 + 复购订单）÷ 购买访客',ha='center',transform=ax.transAxes,fontsize=11)
    ax.text(.5,.15,'全观察期 · 严格路径可跨商品、跨会话 · 其他路径含记录不完整或顺序不符合的购买',ha='center',transform=ax.transAxes,fontsize=9,color=GRAY)
    fig.suptitle('订单数指标树',fontsize=17,y=.98)
    return fig

def metric_tree_weekly():
    frame=table('11_metric_tree_weekly'); frame=frame[frame.comparable==True]
    cols=['traffic_effect','cart_rate_effect','purchase_rate_effect','other_buyer_effect','repeat_share_effect','repeat_frequency_effect']
    labels=['浏览访客','浏览→加购率','加购→购买率','其他购买访客','复购者占比','复购者额外订单']
    fig,ax=plt.subplots(figsize=(14,6));x=np.arange(len(frame)); positive=np.zeros(len(x));negative=np.zeros(len(x))
    for col,label,color in zip(cols,labels,['#285D92','#54A0A1','#79B77C','#D2A149','#C57933','#9D6AA8']):
        values=frame[col].to_numpy();bottom=np.where(values>=0,positive,negative)
        ax.bar(x,values,bottom=bottom,label=label,color=color,width=.72)
        positive+=np.maximum(values,0);negative+=np.minimum(values,0)
    ax.plot(x,frame.order_change,'ko-',lw=1.3,ms=3,label='订单变化')
    ax.axhline(0,color=GRAY,lw=.8);ax.set_xticks(x,frame.week_start.str[5:],rotation=45,ha='right')
    ax.set_ylabel('相对前周的订单变化（单）');ax.set_title('周订单变化：连乘替代分解',loc='left',pad=12)
    ax.legend(ncol=4,loc='upper center',bbox_to_anchor=(.5,-.22),frameon=False,fontsize=9)
    fig.text(.08,.015,'完整 UTC 自然周；因素依次替换，结果受替换顺序影响；贡献是算术分解，不代表因果',fontsize=9,color=GRAY)
    fig.subplots_adjust(left=.08,right=.98,top=.90,bottom=.32)
    return fig

PLOTS={'funnel':funnel,'sessions':sessions,'retention':retention,'products':products,'metric_tree':metric_tree,'metric_tree_weekly':metric_tree_weekly}
def build_figures():
    style();folder=ROOT/'results/figures';folder.mkdir(exist_ok=True)
    for name,function in PLOTS.items():
        fig=function();fig.savefig(folder/f'{name}.png',dpi=180);fig.savefig(folder/f'{name}.svg');plt.close(fig)
    print('Saved PNG/SVG figures')
if __name__=='__main__':build_figures()
