import test from 'node:test';
import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {scryptSync,randomBytes} from 'node:crypto';
import {mkdtemp,writeFile,rm} from 'node:fs/promises';
import {createHandler} from '../scripts/host.mjs';
test('private host requires authentication and supplies isolation headers',async()=>{
  const root=await mkdtemp('/tmp/ios-web-host-');
  await writeFile(root+'/index.html','<!doctype html><title>host test</title>');
  await writeFile(root+'/.private','must not be served');
  const salt=randomBytes(16),password='test-only-password';
  const credentials={username:'admin',salt:salt.toString('hex'),key:scryptSync(password,salt,64).toString('hex')};
  const server=createServer(createHandler({root,credentials}));
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base='http://127.0.0.1:'+server.address().port;
  try{
    assert.equal((await fetch(base)).status,401);
    const headers={Authorization:'Basic '+Buffer.from('admin:'+password).toString('base64')};
    const page=await fetch(base,{headers});assert.equal(page.status,200);
    assert.equal(page.headers.get('Cross-Origin-Opener-Policy'),'same-origin');
    assert.equal(page.headers.get('Cross-Origin-Embedder-Policy'),'require-corp');
    assert.equal((await fetch(base+'/%2eprivate',{headers})).status,403);
    assert.equal((await fetch(base,{method:'POST',headers})).status,405);
    const status=await(await fetch(base+'/admin',{headers})).json();
    assert.equal(status.runtime,'not-built');assert.equal(status.iosBootVerified,false);
  }finally{await new Promise(resolve=>server.close(resolve));await rm(root,{recursive:true,force:true});}
});
