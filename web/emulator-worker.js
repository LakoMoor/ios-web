import {bootArguments, probeArguments} from './config.js';
let runtime, started = false;
let storageWorker;
const send = (type,fields={}) => postMessage({type,...fields});
const fail = error => send('error',{message:error?.message || String(error)});
self.addEventListener('unhandledrejection', event => {event.preventDefault(); fail(event.reason);});
self.onmessage = async ({data}) => {
  try {
    if (data.type === 'start') {
      if (started) throw new Error('Сеанс уже запущен');
      started = true;
      if (!self.crossOriginIsolated || typeof SharedArrayBuffer === 'undefined') throw new Error('SharedArrayBuffer недоступен в Worker');
      const {default:createInferno} = await import('./runtime/inferno.mjs');
      let probe;
      if (data.mode === 'probe') {
        const response = await fetch(new URL(data.config.swap?'./runtime/probe-paged.bin':'./runtime/probe.bin',import.meta.url));
        if (!response.ok) throw new Error('ARM64 probe отсутствует: HTTP '+response.status);
        probe = new Uint8Array(await response.arrayBuffer());
      }
      const args = probe ? probeArguments(data.config.swap) : bootArguments(data.config,data.files);
      send('arguments',{args});
      runtime = await createInferno({
        noInitialRun:true,
        locateFile:path => new URL('./runtime/'+path,import.meta.url).href,
        print:text => send('serial',{text:String(text)+'\n'}),
        printErr:text => send('serial',{text:String(text)+'\n',stderr:true}),
        onAbort:reason => fail(new Error('WASM abort: '+reason)),
        onExit:code => {storageWorker?.terminate();send('exit',{code});},
        preRun:[module => {
          const FS = module.FS;
          FS.mkdir('/input');
          if (probe) FS.writeFile('/probe.bin',probe);
          else {
            const files = Object.entries(data.files).map(([name,file]) => new File([file],name,{lastModified:file.lastModified}));
            FS.mount(module.WORKERFS,{files},'/input');
          }
        }],
      });
      if (data.config.swap) {
        runtime._web_swap_prepare();
        storageWorker = new Worker(new URL('./swap-storage-worker.js',import.meta.url),{type:'module'});
        await new Promise((resolve,reject)=>{
          storageWorker.onerror=event=>reject(new Error(event.message||'Ошибка storage worker'));
          storageWorker.onmessage=({data:message})=>{
            if(message.type==='ready'){send('swap-ready',message);resolve();}
            if(message.type==='error'){fail(new Error('Подкачка: '+message.message));reject(new Error(message.message));}
          };
          storageWorker.postMessage({type:'init',memory:runtime.webSwapMemory,control:runtime._web_swap_mailbox(),data:runtime._web_swap_buffer(),backend:data.config.swapBackend||'auto'});
        });
        runtime._web_swap_config(data.mode==='probe'?64:data.config.swapCache);
        if(data.mode==='probe'){
          send('serial',{text:'[swap] Проверка вытеснения, повторного чтения и границ страниц…\n'});
          if(runtime._web_swap_selftest()!==1)throw new Error('Подкачка повредила данные при повторном чтении');
          send('serial',{text:'[swap] SWAP_ROUNDTRIP_OK · 256 страниц / кэш 64 страницы\n'});
        }
      }
      send('runtime-ready');
      runtime.callMain(args);
    } else if (data.type === 'pointer' && runtime) runtime._web_pointer(data.x,data.y,data.down?1:0);
    else if (data.type === 'pause' && runtime) runtime._web_control(data.paused?1:2);
    else if (data.type === 'shutdown' && runtime) runtime._web_control(3);
  } catch (error) { fail(error); }
};
