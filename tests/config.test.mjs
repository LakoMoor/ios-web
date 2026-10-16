import test from 'node:test';
import assert from 'node:assert/strict';
import {bootArguments,validateConfig,pointerPosition} from '../web/config.js';
const config={machine:'t8030',memory:4096,swap:true,swapCache:256,format:'raw',bootargs:'-v serial=3'};
const files=Object.fromEntries(['kernel','dtb','trustcache','disk','nvram'].map(x=>[x,{size:100,name:'danger,name='+x}]));
test('requires prepared firmware and storage',()=>assert.throws(()=>validateConfig(config,{}),/kernelcache/));
test('builds Apple namespace devices and protects original disk',()=>{
 const args=bootArguments(config,files);
 assert(args.includes('-snapshot'));
 assert(args.includes('apple-nvram,id=nvram,drive=nvram-store,bus=nvme-bus.0,nsid=2'));
 assert(args.includes('nvme-ns,drive=system,bus=nvme-bus.0,nsid=1'));
 assert(!args.join(' ').includes('danger'));
 assert(args.includes('/input/kernel'));
});
test('rejects memory leaving no space in wasm32',()=>assert.throws(()=>validateConfig({...config,memory:8192},files),/памяти/));
test('SEP requires both files',()=>assert.throws(()=>validateConfig(config,{...files,seprom:{size:5}}),/вместе/));
test('pointer accounts for object-fit letterboxing',()=>{
 const rect={left:10,top:20,width:100,height:200};
 assert.deepEqual(pointerPosition(rect,200,200,60,120),{x:16384,y:16384});
 assert.deepEqual(pointerPosition(rect,200,200,10,70),{x:0,y:0});
 assert.deepEqual(pointerPosition(rect,200,200,200,300),{x:32767,y:32767});
});
