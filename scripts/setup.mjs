import {spawnSync} from 'node:child_process';
import {existsSync,mkdirSync,copyFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=new Set(process.argv.slice(2));
const env={...process.env,HYPERFRAMES_NO_TELEMETRY:'1',DO_NOT_TRACK:'1'};
function run(exe,argv,cwd=root){const r=spawnSync(exe,argv,{cwd,env,stdio:'inherit',windowsHide:true,shell:false});if(r.error)throw r.error;if(r.status!==0)throw Error(`${exe} exited ${r.status}`);}
function findPython(){
 const candidates=[[process.env.VIDEO_WORKBENCH_PYTHON,[]],['python3',[]],['python',[]],...(process.platform==='win32'?[['py',['-3.12']]]:[])];
 for(const [exe,prefix] of candidates){if(!exe)continue;const r=spawnSync(exe,[...prefix,'-c','import sys; assert sys.version_info[:2] == (3, 12)'],{windowsHide:true,stdio:'ignore'});if(r.status===0)return [exe,prefix];}
 throw Error('Python 3.12 was not found. Install it or set VIDEO_WORKBENCH_PYTHON.');
}
const npm=process.env.npm_execpath;
if(!npm)throw Error('Run this installer using npm run setup.');
for(const folder of ['workbench','remotion-studio'])run(process.execPath,[npm,'ci','--prefix',path.join(root,folder)]);
run(process.execPath,['scripts/fetch-official-skills.mjs']);
run(process.execPath,['scripts/create-audio.mjs'],path.join(root,'remotion-studio'));
const gsap=path.join(root,'workbench/node_modules/gsap/dist/gsap.min.js');
for(const target of ['workbench/hyperframes-demo/vendor','templates/rock-paper-cut/vendor']){mkdirSync(path.join(root,target),{recursive:true});copyFileSync(gsap,path.join(root,target,'gsap.min.js'));}
if(!args.has('--skip-python')){
 const py=path.join(root,'.venv',process.platform==='win32'?'Scripts/python.exe':'bin/python');
 if(!existsSync(py)){const [exe,prefix]=findPython();run(exe,[...prefix,'-m','venv',path.join(root,'.venv')]);}
 run(py,['-m','pip','install','-r','requirements.txt']);
 if(args.has('--with-alignment'))run(py,['-m','pip','install','-r','requirements-alignment.txt']);
}
if(!args.has('--skip-browser')&&!process.env.VIDEO_WORKBENCH_BROWSER_PATH)run(process.execPath,['node_modules/@remotion/cli/remotion-cli.js','browser','ensure'],path.join(root,'remotion-studio'));
console.log('\nSetup complete. Run npm run doctor, npm run install-skills, then npm start.');
console.log('Audio/lyrics stay local. ASR models are separate: see docs/AI-WORKFLOW.md.');
