import {cp,mkdir,writeFile,stat} from 'node:fs/promises';
await mkdir('dist',{recursive:true});
await cp('web','dist',{recursive:true});
await writeFile('dist/.nojekyll','');
if (process.argv.includes('--require-runtime')) {
  for (const name of ['inferno.mjs','qemu-system-aarch64.wasm','probe.bin','manifest.json']) {
    const s=await stat('dist/runtime/'+name);
    if(!s.size)throw new Error('Runtime file is empty: '+name);
  }
}
console.log('Static site: dist/ (all URLs are relative; GitHub project Pages supported)');
