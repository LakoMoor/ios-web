import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
await mkdir('artifacts',{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
const page=await browser.newPage({viewport:{width:1280,height:1040}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
try {
 await page.goto(process.env.TEST_URL||'http://127.0.0.1:4173/ios-web/');
 await page.waitForFunction(()=>crossOriginIsolated&&document.getElementById('check-coi').textContent==='✓ Готово',null,{timeout:30000});
 const results=[];
 for(const backend of ['opfs','indexeddb']){
  results.push(await page.evaluate(async backend=>{
   const memory=new SharedArrayBuffer(65536+32),control=new Int32Array(memory,0,8),bytes=new Uint8Array(memory,32,65536);
   const worker=new Worker(new URL('./swap-storage-worker.js',location.href),{type:'module'});
   let storageError;
   const ready=new Promise((resolve,reject)=>{worker.onmessage=({data})=>{if(data.type==='ready')resolve(data);else if(data.type==='error'){storageError=data.message;reject(new Error(data.message));}};worker.onerror=e=>reject(new Error(e.message));});
   worker.postMessage({type:'init',memory,control:0,data:32,backend});
   const meta=await ready;
   async function command(op,page){
    Atomics.store(control,1,page);Atomics.store(control,2,0);Atomics.store(control,0,op);Atomics.notify(control,0);
    const deadline=performance.now()+20000;
    while(Atomics.load(control,0)!==0){if(performance.now()>deadline)throw new Error('Storage mailbox timeout');await new Promise(r=>setTimeout(r,1));}
    if(Atomics.load(control,2)!==0)throw new Error(storageError||'Storage I/O failed');
   }
   try{
    await command(1,7);
    if(bytes.some(x=>x!==0))throw new Error('Unwritten page must be zero');
    for(let i=0;i<bytes.length;i++)bytes[i]=(i*31+17)&255;
    await command(2,11);
    bytes.fill(0);
    await command(2,12);
    await command(1,11);
    for(let i=0;i<bytes.length;i++)if(bytes[i]!==((i*31+17)&255))throw new Error('Page roundtrip mismatch at '+i);
    await command(2,65535);
    bytes.fill(0);
    await command(1,65535);
    for(let i=0;i<bytes.length;i++)if(bytes[i]!==((i*31+17)&255))throw new Error('High page roundtrip mismatch at '+i);
    if(meta.backend==='opfs'){
     const root=await navigator.storage.getDirectory();const dir=await root.getDirectoryHandle('ios-web-swap-v1');
     let size=0;for await(const [name,file] of dir.entries())if(name.startsWith('session-'))size+=(await file.getFile()).size;
     if(size!==3*65536)throw new Error('OPFS must compact three pages instead of reserving a sparse 4 GiB file: '+size);
    }
    await command(4,0);
    await command(1,11);
    if(bytes.some(x=>x!==0))throw new Error('Reset did not clear page');
    await command(3,0);
    return {backend:meta.backend,zeroFill:true,roundtripBytes:65536,highPage:65535,compact:meta.backend==='opfs',isolatedPages:true,reset:true,close:true};
   }finally{worker.terminate();}
  },backend));
 }
 await page.screenshot({path:'artifacts/interface.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.screenshot({path:'artifacts/mobile.png',fullPage:true});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 assert.deepEqual(errors,[]);
 await writeFile('artifacts/storage-result.json',JSON.stringify({isolation:'service worker / no host headers',projectPath:'/ios-web/',results,pageErrors:errors},null,2));
 console.log(JSON.stringify(results));
}finally{await browser.close();}
