from pathlib import Path


stylesheet = Path(__file__).with_name("global.css")

with stylesheet.open('r', encoding='utf-8') as f:
    lines = f.readlines()
cut = 0
for i, line in enumerate(lines):
    if 'WORKBENCH' in line:
        cut = i
        break
new = '''/* DASHBOARD (Bento) */
.db-hero{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;}
.db-hero-card{position:relative;background:var(--color-bg-elevated);border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:18px 20px 14px;transition:all var(--duration-fast) var(--ease-out);}
.db-hero-card:hover{box-shadow:var(--shadow-md);transform:translateY(-1px);}
.db-hero-top{display:flex;align-items:baseline;gap:8px;}
.db-hero-num{font-size:30px;font-weight:700;font-family:var(--font-mono);letter-spacing:-.03em;color:var(--text-primary);}
.db-hero-num.brand{color:var(--color-brand);}.db-hero-num.green{color:var(--color-success);}.db-hero-num.amber{color:var(--color-warning);}.db-hero-num.rose{color:var(--color-danger);}
.db-hero-change{font-size:12px;font-weight:700;font-family:var(--font-mono);}
.db-hero-change.up{color:var(--color-success);}.db-hero-change.down{color:var(--color-danger);}
.db-hero-label{font-size:12.5px;color:var(--text-muted);margin-top:2px;}
.db-hero-action{position:absolute;top:10px;right:12px;width:26px;height:26px;border:none;background:transparent;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;color:var(--text-muted);cursor:pointer;font-size:14px;opacity:0;transition:all var(--duration-fast) var(--ease-out);}
.db-hero-card:hover .db-hero-action{opacity:1;}
.db-hero-action:hover{background:var(--color-bg-muted);color:var(--color-brand);}
.db-exec-row{display:grid;grid-template-columns:7fr 3fr;gap:16px;margin-bottom:16px;min-height:340px;}
.db-kanban-item{padding:14px 0;}.db-kanban-item+.db-kanban-item{border-top:1px solid var(--color-border-light);}
.db-kanban-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;}
.db-kanban-title{font-size:14px;font-weight:600;color:var(--text-primary);}
.db-kanban-actions{display:flex;gap:2px;opacity:0;transition:opacity var(--duration-fast);}
.db-kanban-item:hover .db-kanban-actions{opacity:1;}
.db-kanban-stages{display:flex;gap:2px;margin-bottom:6px;}
.db-stage{min-width:48px;text-align:center;padding:6px 8px;background:var(--color-bg-muted);border-radius:var(--radius-sm);}
.db-stage-count{display:block;font-size:18px;font-weight:700;font-family:var(--font-mono);color:var(--text-primary);}
.db-stage-name{display:block;font-size:10px;color:var(--text-muted);margin-top:1px;}
.db-kanban-bar{display:flex;height:6px;border-radius:var(--radius-full);overflow:hidden;background:var(--color-bg-muted);}
.db-kanban-seg{transition:width .6s var(--ease-out);min-width:0;}.db-kanban-seg:first-child{border-radius:var(--radius-full) 0 0 var(--radius-full);}.db-kanban-seg:last-child{border-radius:0 var(--radius-full) var(--radius-full) 0;}
.db-match-item{display:flex;align-items:center;gap:10px;padding:10px 0;cursor:pointer;border-radius:var(--radius-sm);margin:0 -8px;padding-left:8px;padding-right:8px;transition:background var(--duration-fast);}
.db-match-item+.db-match-item{border-top:1px solid var(--color-border-light);}
.db-match-item:hover{background:var(--color-brand-light);}
.db-match-avatar{width:34px;height:34px;border-radius:var(--radius-full);background:linear-gradient(135deg,var(--color-brand),#7b8ff7);color:#fff;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0;}
.db-match-body{flex:1;min-width:0;}
.db-match-name{font-size:13px;font-weight:600;color:var(--text-primary);display:flex;align-items:center;gap:4px;}
.db-match-pos{font-size:11px;color:var(--text-muted);margin-top:1px;}
.db-match-gap{font-size:11px;color:var(--color-danger);margin-top:1px;}
.db-match-score{flex-shrink:0;}
.db-match-pop-btn{width:22px;height:22px;border:none;background:transparent;border-radius:var(--radius-sm);display:flex;align-items:center;justify-content:center;color:var(--text-muted);cursor:pointer;opacity:0;transition:all var(--duration-fast);}
.db-match-item:hover .db-match-pop-btn{opacity:1;}
.db-match-pop-btn:hover{background:var(--color-bg-muted);color:var(--text-primary);}
.db-pop-content{font-size:13px;}.db-pop-row{display:flex;justify-content:space-between;padding:4px 0;}
.db-pop-row span{color:var(--text-muted);}.db-pop-tags{display:flex;gap:4px;flex-wrap:wrap;}
.db-insight-row{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.db-hot-row{display:flex;align-items:center;padding:8px 0;gap:8px;}.db-hot-row+.db-hot-row{border-top:1px solid var(--color-border-light);}
.db-hot-header{padding:6px 0;}.db-hot-col.rank{width:24px;text-align:center;font-size:11px;font-weight:700;color:var(--text-muted);flex-shrink:0;}
.db-hot-col.rank.top{color:var(--color-brand);}
.db-hot-col.name{flex:1;min-width:0;font-size:13px;font-weight:500;}
.db-hot-col.chart{width:100px;flex-shrink:0;display:flex;align-items:center;justify-content:center;}.db-hot-col.num{width:50px;text-align:right;flex-shrink:0;font-size:12px;display:flex;align-items:center;justify-content:flex-end;}
.db-hot-col.trend{width:55px;text-align:right;flex-shrink:0;font-size:12px;display:flex;align-items:center;justify-content:flex-end;}
.db-hot-col.action{width:32px;text-align:right;flex-shrink:0;}
.db-hot-col.trend.up{color:var(--color-success);}.db-hot-col.trend.down{color:var(--color-danger);}
.db-hot-header .db-hot-col{font-size:11px;color:var(--text-muted);font-weight:600;}
.db-skill-list{display:flex;flex-direction:column;}
.db-skill-item{display:flex;align-items:center;gap:12px;padding:12px 0;}.db-skill-item+.db-skill-item{border-top:1px solid var(--color-border-light);}
.db-skill-rank{width:26px;height:26px;border-radius:var(--radius-sm);background:var(--color-bg-muted);color:var(--text-muted);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0;}
.db-skill-rank.hot{background:var(--color-brand-light);color:var(--color-brand);}
.db-skill-body{flex:1;min-width:0;}.db-skill-name{font-size:14px;font-weight:600;color:var(--text-primary);}
.db-skill-combo{font-size:11px;color:var(--text-muted);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.db-skill-right{display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;}
.db-skill-growth{font-size:13px;font-weight:700;font-family:var(--font-mono);color:var(--text-secondary);}
.db-skill-growth.hot{color:var(--color-success);}
.db-drawer{padding:0 4px;}
.db-drawer-header{display:flex;align-items:center;gap:14px;}
.db-drawer-avatar{width:56px;height:56px;border-radius:var(--radius-full);background:linear-gradient(135deg,var(--color-brand),#7b8ff7);color:#fff;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;flex-shrink:0;}
.db-drawer-header h2{font-size:18px;font-weight:700;}
.db-drawer-header p{font-size:13px;color:var(--text-muted);margin-top:2px;}
.db-drawer-header .score-ring{margin-left:auto;flex-shrink:0;}
.db-drawer-section{margin-top:20px;}.db-drawer-section h4{font-size:14px;font-weight:600;margin-bottom:10px;}
.db-drawer-footer{margin-top:24px;padding-top:16px;border-top:1px solid var(--color-border-light);}
.score-ring{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--color-success);background:conic-gradient(var(--color-success) calc(var(--pct) * 1%), var(--color-bg-muted) 0);position:relative;}
.score-ring::before{content:'';position:absolute;inset:3px;background:var(--color-bg-elevated);border-radius:50%;}
.score-ring span{position:relative;z-index:1;}
.db-drawer-header .score-ring{width:56px;height:56px;font-size:14px;}
.db-drawer-header .score-ring::before{inset:4px;}
'''
result = ''.join(lines[:cut]) + new
with stylesheet.open('w', encoding='utf-8') as f:
    f.write(result)
print('done, replaced from line', cut+1)
