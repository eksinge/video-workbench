import {readdirSync,existsSync,mkdirSync,cpSync,readFileSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const argv=process.argv.slice(2),idx=argv.indexOf('--dir');
const target=path.resolve(idx>=0?argv[idx+1]:path.join(process.env.CODEX_HOME||path.join(os.homedir(),'.codex'),'skills'));
const replace=argv.includes('--replace');mkdirSync(target,{recursive:true});
const installed=[],preserved=[];
for(const name of readdirSync(path.join(root,'skills'))){
 const src=path.join(root,'skills',name),dst=path.join(target,name);
 if(!existsSync(path.join(src,'SKILL.md')))continue;
 if(existsSync(dst)&&!replace){preserved.push(name);continue;}
 cpSync(src,dst,{recursive:true,force:replace,filter:file=>!file.includes('__pycache__')&&!file.endsWith('.pyc')});installed.push(name);
}
console.log(JSON.stringify({target,installed:installed.length,preserved:preserved.length,preservedNames:preserved},null,2));
if(preserved.length)console.log('Existing skills were preserved. Review before using --replace, or choose --dir for another agent.');
