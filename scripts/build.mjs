import {cp,mkdir,writeFile,stat,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
await mkdir('dist',{recursive:true});
await cp('web','dist',{recursive:true});
await cp('LICENSE','dist/LICENSE');
await cp('THIRD_PARTY.md','dist/THIRD_PARTY.md');
await cp('third_party','dist/third_party',{recursive:true});
await writeFile('dist/.nojekyll','');
if (process.argv.includes('--require-runtime')) {
  const manifest=JSON.parse(await readFile('dist/runtime/manifest.json','utf8'));
  for (const name of ['inferno.mjs','qemu-system-aarch64.wasm','probe.elf','probe-paged.elf','manifest.json']) {
    const s=await stat('dist/runtime/'+name);
    if(!s.size)throw new Error('Runtime file is empty: '+name);
    if(name!=='manifest.json'){
      const entry=manifest.files?.[name];
      const hash=createHash('sha256').update(await readFile('dist/runtime/'+name)).digest('hex');
      if(!entry||entry.bytes!==s.size||entry.sha256!==hash)throw new Error('Runtime integrity check failed: '+name);
    }
  }
}
console.log('Static site: dist/ (all URLs are relative; GitHub project Pages supported)');
