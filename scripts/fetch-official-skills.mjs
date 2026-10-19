import {spawnSync} from 'node:child_process';
import {existsSync,mkdirSync,readFileSync,writeFileSync,cpSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const manifest=JSON.parse(readFileSync(path.join(root,'workbench/skills-inventory.json'),'utf8'));
const groups=new Map();
for(const skill of manifest.skills){
 if(!/^[a-z0-9-]+$/.test(skill.name)||!/^\w[\w-]*\/[\w.-]+$/.test(skill.repository)||!/^[a-f0-9]{40}$/.test(skill.commit))throw Error('Invalid pinned upstream skill entry');
 const key=skill.repository+'@'+skill.commit;
 if(!groups.has(key))groups.set(key,[]);groups.get(key).push(skill);
}
const git=(args,cwd)=>{const r=spawnSync('git',['-c','core.longpaths=true',...args],{cwd,stdio:'inherit',windowsHide:true});if(r.status!==0)throw Error('Pinned official skill checkout failed; keep previous files and inspect the Git error.');};
for(const [key,list] of groups){
 const sample=list[0],cache=path.join(root,'.runtime/upstream',sample.repository.replace('/','-'));
 const marker=path.join(cache,'.installed-revision');
 if(existsSync(marker)&&readFileSync(marker,'utf8').trim()===sample.commit&&list.every(s=>existsSync(path.join(root,'skills',s.name,'SKILL.md')))){console.log('Pinned skills already ready:',key);continue;}
 mkdirSync(cache,{recursive:true});
 if(!existsSync(path.join(cache,'.git'))){git(['init'],cache);git(['remote','add','origin',`https://github.com/${sample.repository}.git`],cache);}
 git(['sparse-checkout','init','--cone'],cache);git(['sparse-checkout','set','skills'],cache);
 git(['fetch','--depth=1','--filter=blob:none','origin',sample.commit],cache);
 git(['checkout','--detach','FETCH_HEAD'],cache);
 for(const s of list){
  const src=path.join(cache,'skills',s.name),dst=path.join(root,'skills',s.name);
  if(!existsSync(path.join(src,'SKILL.md')))throw Error('Pinned upstream does not contain expected skill: '+s.name);
  cpSync(src,dst,{recursive:true,force:true,filter:file=>!file.includes('__pycache__')&&!file.endsWith('.pyc')});
 }
 writeFileSync(marker,sample.commit+'\n');console.log(`Installed ${list.length} skills from ${key}`);
}
