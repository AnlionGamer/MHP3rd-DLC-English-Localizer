"""Standalone offline HTML renderer for read-only analysis JSON. No external assets."""
from html import escape

CSS='''
:root {color-scheme:light;--ink:#162331;--muted:#596878;--border:#d9e0e6;--bg:#f4f6f8;--card:#fff;--ok:#146548;--warn:#945b0d}
*{box-sizing:border-box}body{font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
main{max-width:1180px;margin:32px auto;padding:0 22px 48px}h1{font-size:27px;letter-spacing:-.5px;margin:7px 0}h2{font-size:20px;margin:25px 0 12px}h3{font-size:17px;margin:0 0 8px}
small,.small{font-size:13px;color:var(--muted)}.eyebrow{text-transform:uppercase;letter-spacing:1.2px;font-size:12px;font-weight:700;color:var(--muted)}
.panel{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;margin-top:16px;box-shadow:0 2px 6px #16233106}
.pill{display:inline-block;background:#e3ece8;color:var(--ok);font-size:12px;padding:3px 9px;border-radius:12px;font-weight:700}
.pill.warn{background:#faeddb;color:var(--warn)}.pill.neutral{background:#ecf0f3;color:#52616b}
.counts{display:flex;flex-wrap:wrap;gap:8px}.count{border:1px solid var(--border);background:#fcfdfe;border-radius:8px;padding:11px 14px;min-width:170px}
.count b{display:block;font-size:23px}.count span{font-size:12px;color:var(--muted)}
.line{display:flex;gap:12px;flex-wrap:wrap;justify-content:space-between;border-bottom:1px solid var(--border);padding:9px 0}.line:last-child{border-bottom:0}
code{font:12px/1.45 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere}
summary{cursor:pointer;display:flex;align-items:center;gap:11px;padding:12px;list-style:none}summary::-webkit-details-marker{display:none}summary:before{content:'›';font-size:23px;color:#5b6977;line-height:0}details[open]>summary:before{content:'⌄';font-size:16px}
details.record{border:1px solid var(--border);border-radius:8px;background:#fff;margin:7px 0;overflow:hidden}
.record-title{flex:1;font-weight:650}.meta{font-size:12px;color:var(--muted);font-weight:400}.details-content{padding:0 15px 13px;border-top:1px solid var(--border)}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:12px}td,th{padding:7px 10px;border-bottom:1px solid var(--border);text-align:left;vertical-align:top}th{color:var(--muted);font-weight:600}td{white-space:pre-wrap;overflow-wrap:anywhere}
.notice{border-left:3px solid #b98026;padding-left:12px;color:#544a3b}.footer{font-size:13px;color:var(--muted);margin-top:24px}
@media(max-width:650px){main{margin:16px auto;padding:0 12px}summary{flex-wrap:wrap}.count{min-width:135px;flex:1}}
'''

def esc(v):return escape(str(v),quote=True)

def pill(status):
    k = ('warn' if status.startswith(('skipped','protected','blocked')) or status=='unsupported'
         else 'neutral' if status.startswith('preserved') else '')
    return '<span class="pill '+k+'">'+esc(status.replace('_',' '))+'</span>'

def table_for_record(r):
    fields=r.get('language_fields',{})
    if not fields:return ''
    english=r.get('proposed_english_fields',{})
    if not english:
        english={'name':r.get('proposed_english_name',''), 'comment':r.get('proposed_english_comment',''), 'owner':r.get('proposed_english_owner','')}
    rows=[]
    for field,language in fields.items():
        proposal=english.get(field,'Original identity, localized display' if field=='owner' else '')
        rows.append('<tr><td>'+esc(field)+'</td><td>'+esc(language)+'</td><td>'+esc(proposal)+'</td></tr>')
    return '<table><thead><tr><th>Text field</th><th>Detected</th><th>English reference / policy</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>'

def record_html(r):
    title=r.get('title') or r.get('name') or r.get('id') or 'Unrecognized record'
    ident=r.get('id') or 'unknown ID'
    slot=r.get('slot','?')
    if 'hunter_slot' in r:slot='hunter '+str(r['hunter_slot']+1)+' / Palico '+str(slot+1)
    source= '<p class="small">Source: '+esc(r['translation_source'])+'</p>' if r.get('translation_source') else ''
    palico_notes=''
    if r.get('editorial'):
        palico_notes='<p><b>Original source name:</b> '+esc(r.get('original_name',''))+'</p>'+ \
          '<p><b>Original comment:</b> '+esc(r.get('original_comment',''))+'</p>'+ \
          '<p><b>Original Meowster (reference):</b> '+esc(r.get('original_creator',''))+'</p>'+ \
          ''.join('<p><b>'+esc(k.replace('_',' ').title())+':</b> '+esc(v)+'</p>' for k,v in r['editorial'].items())
    return ('<details class="record"><summary><span class="record-title">'+esc(title)+
            ' <span class="meta">['+esc(ident)+', slot '+esc(slot)+']</span></span>'+pill(r['status'])+'</summary>'+ 
            '<div class="details-content"><p><b>Planned action:</b> '+esc(r['planned_action'])+'</p>'+ 
            '<p><b>Why:</b> '+esc(r.get('reason','Not specified'))+'</p>'+source+palico_notes+table_for_record(r)+'</div></details>')

def render_html(report):
    blocks=[]
    for s in report['save_sets']:
        cnt=s['preview']['record_status_counts']
        count_html=''.join('<div class="count"><b>'+esc(v)+'</b><span>'+esc(k.replace('_',' '))+'</span></div>' for k,v in sorted(cnt.items()))
        containers=[];records=[]
        for name,c in s['containers'].items():
            status=c['status'];text=f'{name} — {c.get("encryption","undetermined")} — {status}'
            other=('; '.join(c.get('errors',[])))
            containers.append('<div class="line"><b>'+esc(text)+'</b>'+pill(status)+'</div>'+('<p class="notice">'+esc(other)+'</p>' if other else ''))
            for category in ('quest_inventory','palico_inventory','hired_palico_inventory'):
                if category not in c:continue
                recs=c[category].get('records',[])
                records.append('<h3>'+esc('DLC quests' if category=='quest_inventory' else 'Recruited promotional Palicoes (per hunter)' if category=='hired_palico_inventory' else 'Downloaded promotional Palicoes')+' ('+str(len(recs))+')</h3>')
                records.extend(record_html(r) for r in recs)
                if category=='quest_inventory':
                    records.append('<p class="small">Missing catalog quests (not installed): '+esc(len(c[category]['missing_known_quest_ids']))+'. Missing entries are not injected.</p>')
        warning='<p class="notice">Partial/unknown content detected. A future patcher must request explicit approval and preserve skipped records.</p>' if s['preview']['partial_approval_required'] else ''
        blocks.append('<section class="panel"><h2>Save set: '+esc(s['save_set'])+'</h2>'+''.join(containers)+ 
             '<h3>Planned record disposition</h3><p class="small">Selected and eligible / already English / preserved by choice / skipped or blocked are distinct results. Skips will require user approval before any future patch.</p><div class="counts">'+count_html+'</div>'+warning+'</section>'+ 
             '<section class="panel"><h2>Per-record review</h2><p class="small">Expand any record to see validation details and proposed English text.</p>'+''.join(records)+'</section>')
    limitations=''.join('<li>'+esc(l)+'</li>' for l in report['limitations'])
    qa=report.get('catalog_quality',{})
    qa_html='<section class="panel"><h2>Translation catalog quality</h2><p>'+str(len(qa.get('errors',[])))+' blocking error(s); '+str(len(qa.get('warnings',[])))+' advisory notice(s).</p>'+''.join('<p class="notice">'+esc(x['record']+' / '+x['field']+': '+x['reason'])+'</p>' for x in qa.get('errors',[])+qa.get('warnings',[]))+'</section>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+
            '<title>MHP3rd — DLC Analyze Report</title><style>'+CSS+'</style></head><body><main>'+ 
            '<div class="eyebrow">Monster Hunter Portable 3rd • DLC localization</div><h1>Read-only Analyze Report</h1>'+ 
            '<span class="pill">Read-only analysis</span><p>Eligible means proposed for translation, not successfully patched. No game files were written by this analyzer. Palicoes not selected are preserved by choice, not omitted due to an error.</p>'+ 
            '<section class="panel"><h3>Source and plan identity</h3><div class="line"><span>Source</span><code>'+esc(report['source_path'])+'</code></div>'+ 
            '<div class="line"><span>Catalog</span><code>'+esc(report['catalog_sha256'])+'</code></div>'+ 
            '<div class="line"><span>Patch authorization</span><code>Not included in shareable HTML</code></div>'+ 
            '<div class="line"><span>Quest localization</span><b>'+esc('selected' if report['options']['quests'] else 'not selected')+'</b></div>'+ 
            '<div class="line"><span>Optional Palicoes</span><b>'+esc(', '.join(report['options']['palico_ids']) or 'none')+'</b></div>'+
            '<div class="line"><span>Update already recruited</span><b>'+esc('selected' if report['options'].get('hired_palicoes') else 'not selected')+'</b></div></section>'+ 
            qa_html+''.join(blocks)+'<section class="panel"><h2>Limits and safety commitments</h2><ul>'+limitations+'</ul></section>'+ 
            '<p class="footer">Analysis v'+esc(report['analyzer_version'])+' · Offline report · No scripts, network connections or embedded save data.</p></main></body></html>')
