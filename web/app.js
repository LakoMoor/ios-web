import {roles,validateConfig,pointerPosition} from './config.js';
import {ensureIsolation} from './isolation.js';
const $ = id => document.getElementById(id);
const selected = {};
let worker, runtimeReady=false, active=false, paused=false, mode='', startedAt=0, frameCount=0, startupTimer, runtimeAvailable=false, browserReady=false;
const log = text => {const el=$('console');el.textContent=(el.textContent+text).slice(-150000);el.scrollTop=el.scrollHeight;};
const status = (text,state='') => {$('status').textContent=text;$('status-dot').className=state;document.body.dataset.state=state||'idle';};
function error(message) {$('config-error').textContent=message;$('config-error').hidden=false;}
function controls() {
  $('start').disabled=active||!browserReady||!runtimeAvailable;
  $('probe').disabled=active||!browserReady||!runtimeAvailable;
  $('pause').disabled=!runtimeReady;
  $('stop').disabled=!active;
  $('capture').disabled=frameCount===0;
  document.querySelectorAll('.setup input,.setup select').forEach(el=>el.disabled=active);
}
for (const [id,title,hint,required] of roles) {
  const label=document.createElement('label');label.className='file-row';label.htmlFor='file-'+id;
  const icon=document.createElement('span');icon.className='file-icon';icon.textContent='⌑';
  const text=document.createElement('span');text.className='file-text';
  const name=document.createElement('b');name.textContent=title+(required?' *':'');
  const help=document.createElement('small');help.textContent=hint;
  const add=document.createElement('span');add.className='file-add';add.textContent='+';
  const input=document.createElement('input');input.type='file';input.id='file-'+id;input.setAttribute('aria-label',title);
  input.onchange=()=>{const file=input.files[0];if(file)selected[id]=file;else delete selected[id];name.textContent=file?.name||title+(required?' *':'');help.textContent=file?(file.size/1048576).toFixed(2)+' МБ · локальный файл':hint;label.classList.toggle('selected',!!file);add.textContent=file?'✓':'+';$('file-count').textContent=roles.filter(([key,,,req])=>req&&selected[key]).length+' / 5';$('config-error').hidden=true;};
  text.append(name,help);label.append(icon,text,add,input);$(required?'files':'extra-files').append(label);
}
$('file-count').textContent='0 / 5';
const readConfig=()=>({machine:$('machine').value,memory:Number($('memory').value),bootargs:$('bootargs').value,format:$('format').value,swap:$('swap').checked,swapCache:Number($('swap-cache').value),swapBackend:$('swap-backend').value});
try {const stored=JSON.parse(localStorage.getItem('ios-web-config')||'null');if(stored){if(['t8030','s8000'].includes(stored.machine))$('machine').value=stored.machine;if(Number.isInteger(stored.memory)&&stored.memory>=512&&stored.memory<=2560)$('memory').value=stored.memory;}} catch {}
function updateConfig() {$('memory-value').textContent=$('memory').value+' МБ';$('chip-version').textContent=$('machine').value==='t8030'?'13':'9';$('machine-label').textContent=$('machine').value.toUpperCase()+' / AARCH64';try{localStorage.setItem('ios-web-config',JSON.stringify(readConfig()));}catch{}}
$('swap').onchange=()=>{$('memory').max=$('swap').checked?'4096':'1792';if(Number($('memory').value)>Number($('memory').max))$('memory').value=$('memory').max;updateConfig();};$('memory').oninput=updateConfig;$('machine').onchange=updateConfig;updateConfig();
function finish(message,state='') {
  clearTimeout(startupTimer);worker?.terminate();worker=null;active=false;runtimeReady=false;paused=false;
  $('pause').textContent='Ⅱ Пауза';status(message,state);controls();
}
function fail(message) {log('[ERROR] '+message+'\n');error(message);finish('Ошибка запуска','failed');$('screen-title').textContent='Запуск остановлен';$('screen-description').textContent='Подробности доступны в консоли.';}
async function start(nextMode) {
  const config=readConfig();
  if(nextMode==='ios'){try{validateConfig(config,selected);}catch(e){error(e.message);return;}}
  $('config-error').hidden=true;frameCount=0;$('frames').textContent='—';$('console').textContent='';
  $('screen').hidden=true;$('screen-empty').hidden=false;$('screen-title').textContent='Загрузка движка…';$('screen-description').textContent='Компиляция WebAssembly может занять некоторое время.';$('screen-badge').textContent=nextMode==='probe'?'ARM64 / ДИАГНОСТИКА':'WEBASSEMBLY / TCI';
  mode=nextMode;active=true;paused=false;startedAt=performance.now();runtimeReady=false;controls();status('Загрузка WebAssembly','active');$('console-state').textContent='/ запуск';
  worker=new Worker(new URL('./emulator-worker.js',import.meta.url),{type:'module'});
  worker.onerror=event=>{event.preventDefault();fail(event.message||'Ошибка Worker');};
  worker.onmessage=({data})=>{
    if(data.type==='serial') {
      log(data.text);
      if(mode==='probe'&&data.text.includes('INFERNO_WASM_ARM64_OK')){
        clearTimeout(startupTimer);status('ARM64: тест пройден','active');$('screen-title').textContent='ARM64 работает.';$('screen-description').textContent='Гостевая программа выполнена на Inferno / WebAssembly. Результат — в консоли.';$('screen-badge').textContent='INFERNO_WASM_ARM64_OK';document.body.dataset.probe='passed';$('console-state').textContent='/ ARM64 OK';
      }
    } else if(data.type==='arguments') log('$ qemu-system-aarch64 '+data.args.map(x=>x.includes(' ')?JSON.stringify(x):x).join(' ')+'\n\n');
    else if(data.type==='swap-ready'){$('swap-status').textContent=data.backend.toUpperCase();log('[swap] '+data.backend.toUpperCase()+' · кэш '+(mode==='probe'?64:config.swapCache)+' МБ\n');}
    else if(data.type==='runtime-ready') {runtimeReady=true;controls();status('Запуск гостевой системы','active');}
    else if(data.type==='display-ready') {clearTimeout(startupTimer);if(mode==='ios')status('Эмулятор запущен · ожидание iOS','active');}
    else if(data.type==='frame') {
      if(mode==='probe') return;
      const canvas=$('screen');if(canvas.width!==data.width||canvas.height!==data.height){canvas.width=data.width;canvas.height=data.height;}
      canvas.getContext('2d',{alpha:false}).putImageData(new ImageData(new Uint8ClampedArray(data.buffer),data.width,data.height),0,0);
      $('screen-empty').hidden=true;canvas.hidden=false;frameCount++;$('frames').textContent=String(frameCount);controls();
    } else if(data.type==='paused') {paused=data.paused;$('pause').textContent=paused?'▶ Продолжить':'Ⅱ Пауза';status(paused?'Пауза':(mode==='probe'?'ARM64: тест пройден':'Эмулятор запущен'),'active');}
    else if(data.type==='error') fail(data.message);
    else if(data.type==='exit') {log('[exit '+data.code+']\n');finish('Эмулятор завершён',data.code?'failed':'');}
  };
  startupTimer=setTimeout(()=>fail('За 180 секунд движок не запустился. Проверьте консоль и доступную память.'),180000);
  worker.postMessage({type:'start',mode,config,files:nextMode==='ios'?selected:{}});
}
$('start').onclick=()=>start('ios');$('probe').onclick=()=>start('probe');
$('stop').onclick=()=>{finish('Сеанс остановлен');log('\n[Сеанс остановлен. Временные изменения диска удалены.]\n');$('console-state').textContent='/ остановлен';};
$('pause').onclick=()=>worker?.postMessage({type:'pause',paused:!paused});
$('clear-log').onclick=()=>{$('console').textContent='';};
function download(blob,name){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('download-log').onclick=()=>download(new Blob([$('console').textContent],{type:'text/plain;charset=utf-8'}),'ios-web-session.log');
$('capture').onclick=()=>$('screen').toBlob(blob=>{if(blob)download(blob,'ios-web-screen.png');});
$('fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('device-area').requestFullscreen();}catch(e){error('Полный экран недоступен: '+e.message);}};
const canvas=$('screen');
let pointer=null;
function sendPointer(event,down){if(!worker||paused||mode==='probe')return;const pos=pointerPosition(canvas.getBoundingClientRect(),canvas.width,canvas.height,event.clientX,event.clientY);worker.postMessage({type:'pointer',...pos,down});}
canvas.onpointerdown=event=>{if(pointer!==null)return;pointer=event.pointerId;canvas.setPointerCapture(pointer);sendPointer(event,true);};
canvas.onpointermove=event=>{if(pointer===event.pointerId)sendPointer(event,true);};
canvas.onpointerup=canvas.onpointercancel=event=>{if(pointer!==event.pointerId)return;sendPointer(event,false);pointer=null;};
window.addEventListener('blur',()=>{if(pointer!==null){worker?.postMessage({type:'pointer',x:0,y:0,down:false});pointer=null;}});
window.addEventListener('pagehide',()=>worker?.terminate());
setInterval(()=>{if(active){const sec=Math.floor((performance.now()-startedAt)/1000);$('elapsed').textContent=String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0');}},500);
function check(id,ok,label){$(id).textContent=label||(ok?'✓ Готово':'× Нет');$(id).className=ok?'ok':'fail';}
async function init(){
  check('check-wasm',typeof WebAssembly==='object');
  try{if(!await ensureIsolation())return;sessionStorage.removeItem('ios-web-isolation-reload');browserReady=typeof WebAssembly==='object'&&typeof SharedArrayBuffer!=='undefined';}
  catch(e){error(e.message);log('[browser] '+e.message+'\n');}
  check('check-sab',typeof SharedArrayBuffer!=='undefined');check('check-coi',crossOriginIsolated);
  try {const r=await fetch(new URL('./runtime/manifest.json',import.meta.url));if(!r.ok)throw new Error('HTTP '+r.status);const m=await r.json();runtimeAvailable=!!(m.files?.['inferno.mjs']&&m.files?.['qemu-system-aarch64.wasm']);check('check-runtime',runtimeAvailable,runtimeAvailable?'✓ Собран':'× Нет сборки');}
  catch{check('check-runtime',false,'× Нет сборки');log('[build] WASM-модуль отсутствует. Выполните сборку по README.\n');}
  controls();status(browserReady&&runtimeAvailable?'Готов к запуску':'Среда требует настройки',browserReady&&runtimeAvailable?'':'failed');
}
init();
