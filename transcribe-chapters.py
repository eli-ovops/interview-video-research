from pathlib import Path
import json, subprocess, wave, hashlib, time

root = Path(__file__).resolve().parent
source = root / 'source-x.mp4'
chapters = json.loads((root / '0Z-vhBvBmUY.info.json').read_text())['chapters']
ffmpeg = '/Users/USER/.local/bin/ffmpeg'
whisper = '/Volumes/EXTERNAL/Tools/Whisper/bin/whisper-cli'
model = '/Volumes/EXTERNAL/Tools/Whisper/models/ggml-base.bin'
out = root / 'asr'
out.mkdir(exist_ok=True)
sha = hashlib.sha256(source.read_bytes()).hexdigest()
manifest = {'source':str(source),'sha256':sha,'method':'local whisper.cpp base, zh, chapter segmentation','chapters':[],'status':'running'}
started = time.time()
for index, chapter in enumerate(chapters, 1):
    start, end = chapter['start_time'], chapter['end_time']
    prefix = out / f'chapter-{index:02d}'
    audio = prefix.with_suffix('.wav')
    original_prefix = prefix
    existing_json = prefix.with_suffix('.json')
    if existing_json.exists():
        try:
            selected = existing_json
            repair = out / f'chapter-{index:02d}-repair1.json'
            if repair.exists():
                selected = repair
            raw = selected.read_bytes()
            text = raw.decode('utf-8', errors='replace')
            existing = json.loads(text)
            manifest['chapters'].append({'index':index,'start':start,'end':end,'source_title':chapter['title'],'audio':str(audio),'json':str(selected),'status':'transcribed','segments':len(existing.get('transcription',[])),'reused_current_task':True,'unicode_replacement_count':text.count('\ufffd')})
            continue
        except UnicodeDecodeError:
            prefix = out / f'chapter-{index:02d}-repair1'
    logfile = prefix.with_suffix('.log')
    record = {'index':index,'start':start,'end':end,'source_title':chapter['title'],'audio':str(audio),'json':str(prefix.with_suffix('.json')),'status':'running'}
    manifest['chapters'].append(record)
    (root/'asr-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    with logfile.open('w') as log:
        if not audio.exists():
            subprocess.run([ffmpeg,'-nostdin','-hide_banner','-loglevel','error','-n','-ss',str(start),'-i',str(source),'-t',str(end-start),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(audio)],stdout=log,stderr=log,check=True)
        with wave.open(str(audio)) as f:
            duration = f.getnframes()/f.getframerate()
        record['wav_duration'] = duration
        if abs(duration-(end-start)) > .1:
            raise RuntimeError(f'audio length mismatch chapter {index}: {duration}')
        subprocess.run([whisper,'-m',model,'-f',str(audio),'-l','zh','-t','4','-mc','0','-nf','-otxt','-osrt','-oj','-of',str(prefix)],stdout=log,stderr=log,check=True)
    raw=prefix.with_suffix('.json').read_bytes()
    decoded=raw.decode('utf-8',errors='replace')
    d=json.loads(decoded)
    record['unicode_replacement_count']=decoded.count('\ufffd')
    record.update(status='transcribed',segments=len(d.get('transcription',[])),elapsed_total=round(time.time()-started,1),decode_options='no context carry, no temperature fallback, no byte-length splitting')
    if prefix != original_prefix:
        record['initial_invalid_json_retained'] = str(original_prefix.with_suffix('.json'))
    (root/'asr-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(f"chapter {index:02d}/39 transcribed: {start}--{end}, {record['segments']} segments, elapsed {record['elapsed_total']}s",flush=True)
manifest['status']='transcribed_all_chapters'
(root/'asr-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print('All chapters processed. Content review and accuracy checks remain.',flush=True)
