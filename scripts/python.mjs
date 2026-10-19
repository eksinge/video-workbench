import {existsSync} from 'node:fs';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const python=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
if(!existsSync(python))throw Error('Run npm run setup first.');
const r=spawnSync(python,['-X','utf8',...process.argv.slice(2)],{cwd:root,stdio:'inherit',windowsHide:true});
process.exit(r.status??1);
