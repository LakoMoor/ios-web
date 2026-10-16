// SPDX-License-Identifier: AGPL-3.0-only
// The storage worker stays responsive while QEMU pthreads synchronously wait on
// their shared mailbox. No Atomics.wait is ever executed on the window thread.
const PAGE=65536;
let handle,dir,fileName,db,dbName,control,bytes,backend;
const transaction=(mode,run)=>new Promise((resolve,reject)=>{
 const tx=db.transaction('pages',mode);let result;const req=run(tx.objectStore('pages'));
 req.onsuccess=()=>{result=req.result;};tx.oncomplete=()=>resolve(result);
 tx.onerror=tx.onabort=()=>reject(tx.error||new Error('IndexedDB transaction failed'));
});
async function init(data){
 control=new Int32Array(data.memory,data.control,8);
 bytes=new Uint8Array(data.memory,data.data,PAGE);
 const session=crypto.randomUUID();
 if(data.backend!=='indexeddb'&&navigator.storage?.getDirectory){
  try{
   const root=await navigator.storage.getDirectory();dir=await root.getDirectoryHandle('ios-web-swap-v1',{create:true});
   // Old workers release their access handles on termination. Do not touch
   // locked files: they belong to another live session.
   for await(const [name] of dir.entries())if(name.startsWith('session-')){try{await dir.removeEntry(name);}catch{}}
   fileName='session-'+session;const file=await dir.getFileHandle(fileName,{create:true});
   handle=await file.createSyncAccessHandle();backend='opfs';
  }catch(error){if(data.backend==='opfs')throw error;}
 }
 if(!handle){
  dbName='ios-web-swap-'+session;
  db=await new Promise((resolve,reject)=>{const req=indexedDB.open(dbName,1);req.onupgradeneeded=()=>req.result.createObjectStore('pages');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
  backend='indexeddb';
 }
 const estimate=await navigator.storage?.estimate?.();
 postMessage({type:'ready',backend,quota:estimate?.quota,usage:estimate?.usage});
 while(true){
  let op=Atomics.load(control,0);
  if(op===0){
   if(Atomics.waitAsync)await Atomics.waitAsync(control,0,0).value;
   else await new Promise(resolve=>setTimeout(resolve,1));
   continue;
  }
  const page=Atomics.load(control,1)>>>0;
  try{
   if(op===1){
    bytes.fill(0);
    if(handle){const read=handle.read(bytes,{at:page*PAGE});if(read<PAGE)bytes.fill(0,read);}
    else{const stored=await transaction('readonly',store=>store.get(page));if(stored)bytes.set(new Uint8Array(stored));}
    Atomics.add(control,3,1);
   }else if(op===2){
    if(handle){if(handle.write(bytes,{at:page*PAGE})!==PAGE)throw new Error('Short OPFS write');}
    else await transaction('readwrite',store=>store.put(bytes.slice().buffer,page));
    Atomics.add(control,4,1);
   }else if(op===4){
    if(handle){handle.truncate(0);handle.flush();}
    else await transaction('readwrite',store=>store.clear());
   }else if(op===3){
    if(handle){handle.flush();handle.close();handle=null;await dir.removeEntry(fileName);}
    if(db){db.close();indexedDB.deleteDatabase(dbName);db=null;}
   }else throw new Error('Invalid swap operation');
   Atomics.store(control,2,0);
  }catch(error){
   Atomics.store(control,2,-1);postMessage({type:'error',message:error.message||String(error)});
  }
  Atomics.store(control,0,0);Atomics.notify(control,0);
  if(op===3){postMessage({type:'closed'});return;}
 }
}
self.onmessage=({data})=>{if(data.type==='init')init(data).catch(error=>postMessage({type:'error',message:error.message||String(error)}));};
