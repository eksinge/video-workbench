import {spawnSync} from 'node:child_process';
import {existsSync,readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const commands=[
 [process.execPath,['--check','workbench/scripts/workbench.mjs']],
 [process.execPath,['remotion-studio/node_modules/typescript/bin/tsc','--noEmit','--project','remotion-studio/tsconfig.json']],
 [process.execPath,['scripts/python.mjs','scripts/style-self-test.py']]
];
for(const [exe,args] of commands){const p=spawnSync(exe,args,{cwd:root,stdio:'inherit',windowsHide:true});if(p.status!==0)process.exit(p.status??1);}
console.log('Source and subtitle style checks passed. Engine export verification is documented separately.');
