from pathlib import Path
import json, re, subprocess, time

root=Path(__file__).resolve().parent
manifest=json.loads((root/'asr-manifest.json').read_text())
assert manifest['status']=='transcribed_all_chapters'
ranges=[]
for c in manifest['chapters']:
    data=json.loads(Path(c['json']).read_bytes().decode('utf-8',errors='replace'))
    for s in data['transcription']:
        text=s['text'];a=c['start']+s['offsets']['from']/1000;b=c['start']+s['offsets']['to']/1000
        if '\ufffd' in text or re.search(r'(.{1,12})\1{10,}',text):
            if ranges and a<=ranges[-1]['end']+10 and c['index']==ranges[-1]['chapter']:
                ranges[-1]['end']=max(ranges[-1]['end'],b+7)
            else:ranges.append({'chapter':c['index'],'start':max(c['start'],a-7),'end':min(15749.35,max(b,a+5)+7),'reason':'ASR重复或字节损坏'})
(root/'repair-ranges.json').write_text(json.dumps(ranges,ensure_ascii=False,indent=2))
out=root/'repairs';out.mkdir(exist_ok=True)
for index,r in enumerate(ranges,1):
    prefix=out/f'patch-{index:02d}'
    audio=prefix.with_suffix('.wav')
    with prefix.with_suffix('.log').open('w') as log:
        subprocess.run(['/Users/USER/.local/bin/ffmpeg','-nostdin','-hide_banner','-loglevel','error','-n','-ss',str(r['start']),'-i',str(root/'source-x-720.mp4'),'-t',str(r['end']-r['start']),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(audio)],stdout=log,stderr=log,check=True)
        subprocess.run(['/Volumes/EXTERNAL/Tools/Whisper/bin/whisper-cli','-m','/Volumes/EXTERNAL/Tools/Whisper/models/ggml-base.bin','-f',str(audio),'-l','zh','-t','4','-mc','0','-nf','-bs','1','-bo','1','-otxt','-oj','-of',str(prefix)],stdout=log,stderr=log,check=True)
    r.update(json=str(prefix.with_suffix('.json')),audio=str(audio),status='retranscribed_higher_quality_short_window')
    (root/'repair-ranges.json').write_text(json.dumps(ranges,ensure_ascii=False,indent=2))
    print(f"patch {index}/{len(ranges)} chapter {r['chapter']} {r['start']}--{r['end']}",flush=True)
