import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFileSync,writeFileSync,existsSync,mkdirSync,copyFileSync,createReadStream,statSync,openSync,readdirSync} from 'node:fs';
import {spawn,spawnSync} from 'node:child_process';
import {createHash,randomBytes} from 'node:crypto';
import os from 'node:os';

export const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const config=JSON.parse(readFileSync(path.join(root,'workbench.json'),'utf8'));
config.port=Number(process.env.VIDEO_WORKBENCH_PORT||config.port);
config.remotion.port=Number(process.env.REMOTION_PORT||3027);
config.hyperframes.port=Number(process.env.HYPERFRAMES_PORT||config.hyperframes.port);
config.remotion.url=`http://127.0.0.1:${config.remotion.port}/ProjectLaunch`;
config.hyperframes.url=`http://127.0.0.1:${config.hyperframes.port}/#project/hyperframes-demo`;
const ffmpeg=process.env.FFMPEG_PATH||'ffmpeg';
const remotion=path.resolve(root,config.remotion.directory);
const hfProject=path.resolve(root,config.hyperframes.directory);
const hfCLI=path.join(root,'node_modules/hyperframes/bin/hyperframes.mjs');
const remotionCLI=path.join(remotion,'node_modules/@remotion/cli/remotion-cli.js');
const runtime=path.join(root,'.runtime');
for(const dir of [runtime,path.join(root,'exports'),path.join(root,'shared-assets'),path.join(hfProject,'assets'),path.join(hfProject,'vendor')])mkdirSync(dir,{recursive:true});
function findBrowser(dir,depth=0){
  if(!existsSync(dir)||depth>3)return '';
  for(const entry of readdirSync(dir,{withFileTypes:true})){
    const file=path.join(dir,entry.name);
    if(entry.isFile()&&['chrome-headless-shell.exe','chrome-headless-shell'].includes(entry.name))return file;
    if(entry.isDirectory()){const found=findBrowser(file,depth+1);if(found)return found;}
  }return '';
}
const browser=process.env.VIDEO_WORKBENCH_BROWSER_PATH||findBrowser(path.join(remotion,'node_modules/.remotion/chrome-headless-shell'));
const env={...process.env,HYPERFRAMES_NO_TELEMETRY:'1',DO_NOT_TRACK:'1',...(existsSync(browser)?{HYPERFRAMES_BROWSER_PATH:browser}:{})};
const digest=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const copyChanged=(from,to)=>{if(!existsSync(from))throw Error('Missing input: '+from);if(!existsSync(to)||digest(from)!==digest(to))copyFileSync(from,to);};

export async function stage(){
  const records=[];
  const sourceVideo=path.join(remotion,'exports/project-launch.mp4');
  if(!existsSync(sourceVideo))await perform('render','remotion');
  const original=path.join(root,'shared-assets/remotion-original.mp4');
  copyChanged(sourceVideo,original);
  const sourceSha=digest(sourceVideo);
  const proxy=path.join(root,'shared-assets/remotion-input.mp4');
  const proxyMeta=path.join(runtime,'proxy.json');
  const previous=existsSync(proxyMeta)?JSON.parse(readFileSync(proxyMeta,'utf8')):{};
  if(!existsSync(proxy)||previous.sourceSha256!==sourceSha||previous.recipe!=='h264-gop30-v1'){
    await run(ffmpeg,['-hide_banner','-loglevel','error','-y','-i',original,'-c:v','libx264','-preset','fast','-crf','18','-g','30','-keyint_min','30','-sc_threshold','0','-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',proxy]);
    writeFileSync(proxyMeta,JSON.stringify({sourceSha256:sourceSha,recipe:'h264-gop30-v1'}));
  }
  copyChanged(proxy,path.join(hfProject,'assets/remotion-input.mp4'));
  records.push({file:'remotion-input.mp4',source:path.relative(root,sourceVideo),sourceSha256:sourceSha,recipe:'h264-gop30-v1',sha256:digest(proxy),bytes:statSync(proxy).size});
  const from=path.join(remotion,'public/launch.wav');const shared=path.join(root,'shared-assets/launch.wav');
  copyChanged(from,shared);copyChanged(shared,path.join(hfProject,'assets/launch.wav'));
  records.push({file:'launch.wav',source:path.relative(root,from),sha256:digest(shared),bytes:statSync(shared).size});
  copyChanged(path.join(root,'node_modules/gsap/dist/gsap.min.js'),path.join(hfProject,'vendor/gsap.min.js'));
  const manifest={workflow:'Remotion render -> shared assets -> HyperFrames composition',assets:records};
  writeFileSync(path.join(root,'bridge-manifest.json'),JSON.stringify(manifest,null,2));return manifest;
}

const run=(exe,args,cwd=root)=>new Promise((resolve,reject)=>{
  const child=spawn(exe,args,{cwd,env,windowsHide:true,shell:false});
  let log='';const append=data=>{const s=data.toString();log=(log+s).slice(-24000);process.stdout.write(s);};
  child.stdout.on('data',append);child.stderr.on('data',append);child.on('error',reject);
  child.on('close',code=>code===0?resolve(log):reject(Error(`Command exited ${code}\n${log.slice(-4000)}`)));
});
const get=async url=>{try{const r=await fetch(url,{signal:AbortSignal.timeout(1500)});return r.ok;}catch{return false;}};
const isWorkbench=async url=>{try{const r=await fetch(url+'/api/identity',{signal:AbortSignal.timeout(1500)});return r.ok&&(await r.json()).id==='portable-video-workbench-v1';}catch{return false;}};
const listener=port=>new Promise(resolve=>{const socket=net.connect({host:'127.0.0.1',port});socket.setTimeout(700);socket.once('connect',()=>{socket.destroy();resolve(true)});socket.once('error',()=>resolve(false));socket.once('timeout',()=>{socket.destroy();resolve(false)});});

async function launchRemotion(){
  const url=`http://127.0.0.1:${config.remotion.port}`;
  if(await get(url))return;
  if(await listener(config.remotion.port))throw Error('Remotion port belongs to another application; choose REMOTION_PORT.');
  const stdout=openSync(path.join(runtime,'remotion-out.log'),'a'),stderr=openSync(path.join(runtime,'remotion-error.log'),'a');
  const child=spawn(process.execPath,[remotionCLI,'studio','src/index.ts',`--port=${config.remotion.port}`,'--ipv4','--no-open'],{cwd:remotion,env,detached:true,windowsHide:true,stdio:['ignore',stdout,stderr]});
  child.unref();writeFileSync(path.join(runtime,'remotion.pid'),String(child.pid));
  for(let i=0;i<60;i++){if(await get(url))return;await new Promise(r=>setTimeout(r,500));}
  throw Error('Remotion startup timed out; inspect workbench/.runtime/remotion-error.log.');
}

export async function perform(action,engine){
  if(!['remotion','hyperframes'].includes(engine))throw Error('Unknown engine');
  if(action==='preview'){
    if(engine==='remotion')await launchRemotion();
    else {await stage();await run(process.execPath,[hfCLI,'preview',hfProject,'--background','--port',String(config.hyperframes.port),'--no-open','--json']);}
    return {url:config[engine].url};
  }
  if(action==='check'){
    if(engine==='remotion')await run(process.execPath,[path.join(remotion,'node_modules/typescript/bin/tsc'),'--noEmit'],remotion);
    else{await stage();await run(process.execPath,[hfCLI,'check',hfProject,'--at','0.8,3.5,6.9','--timeout','30000','--json']);}
    return {ok:true};
  }
  if(action==='render'){
    if(engine==='remotion')await run(process.execPath,[remotionCLI,'render','src/index.ts','ProjectLaunch','exports/project-launch.mp4','--codec=h264','--crf=18','--pixel-format=yuv420p','--concurrency=1',...(browser?['--browser-executable',browser]:[])],remotion);
    else{await stage();await run(process.execPath,[hfCLI,'render',hfProject,'--output',path.join(root,'exports/integration-demo.mp4'),'--fps','30','--quality','draft','--workers','1','--low-memory-mode']);await run(ffmpeg,['-hide_banner','-loglevel','error','-y','-ss','0.9','-i',path.join(root,'exports/integration-demo.mp4'),'-frames:v','1',path.join(root,'exports/integration-poster.png')]);}
    return {url:engine==='remotion'?'/media/remotion-demo.mp4':'/media/integration-demo.mp4'};
  }
  throw Error('Unsupported action');
}

export function doctor(){
  const inventory=JSON.parse(readFileSync(path.join(root,'skills-inventory.json'),'utf8'));
  const missing=inventory.skills.filter(s=>!existsSync(path.resolve(root,s.path,'SKILL.md'))).map(s=>s.name);
  const version=(file)=>existsSync(file)?JSON.parse(readFileSync(file,'utf8')).version:null;
  const ffmpegCheck=spawnSync(ffmpeg,['-version'],{encoding:'utf8',windowsHide:true});
  return {node:process.version,remotion:version(path.join(remotion,'node_modules/remotion/package.json')),hyperframes:version(path.join(root,'node_modules/hyperframes/package.json')),officialSkills:inventory.skills.length,missingSkills:missing,ffmpeg:ffmpegCheck.status===0,browser:!!browser&&existsSync(browser),sharedAssets:existsSync(path.join(root,'bridge-manifest.json')),exports:{remotion:existsSync(path.join(remotion,'exports/project-launch.mp4')),hyperframes:existsSync(path.join(root,'exports/integration-demo.mp4'))}};
}

export async function start(){
  const url=`http://127.0.0.1:${config.port}`;
  if(await isWorkbench(url))return console.log(url);
  if(await listener(config.port))throw Error(`Port ${config.port} is occupied; no other service was changed.`);
  const stdout=openSync(path.join(runtime,'workbench-out.log'),'a');const stderr=openSync(path.join(runtime,'workbench-error.log'),'a');
  const child=spawn(process.execPath,[fileURLToPath(import.meta.url),'serve'],{cwd:root,env,detached:true,windowsHide:true,stdio:['ignore',stdout,stderr]});
  child.unref();writeFileSync(path.join(runtime,'workbench.pid'),String(child.pid));
  for(let i=0;i<40;i++){if(await isWorkbench(url))return console.log(url);await new Promise(r=>setTimeout(r,250));}
  throw Error('Workbench did not start; see .runtime/workbench-error.log');
}

function sendFile(req,res,file,type){
  if(!existsSync(file)){res.writeHead(404);res.end('Not rendered yet');return;}
  const size=statSync(file).size;const range=req.headers.range;
  if(range){const m=/^bytes=(\d+)-(\d*)$/.exec(range);if(!m){res.writeHead(416);res.end();return;}const a=Number(m[1]),b=m[2]?Math.min(Number(m[2]),size-1):size-1;if(a>b||a>=size){res.writeHead(416,{'Content-Range':`bytes */${size}`});res.end();return;}res.writeHead(206,{'Content-Type':type,'Accept-Ranges':'bytes','Content-Range':`bytes ${a}-${b}/${size}`,'Content-Length':b-a+1});createReadStream(file,{start:a,end:b}).pipe(res);return;}
  res.writeHead(200,{'Content-Type':type,'Content-Length':size,'Accept-Ranges':'bytes'});createReadStream(file).pipe(res);
}

export async function serve(){
  const token=randomBytes(24).toString('hex');let job=null;
  const json=(res,value,status=200)=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(JSON.stringify(value));};
  const server=http.createServer(async(req,res)=>{
    try{
      const pathname=new URL(req.url,'http://127.0.0.1').pathname;
      if(req.method==='GET'&&pathname==='/api/identity')return json(res,{id:'portable-video-workbench-v1'});
      if(req.method==='GET'&&pathname==='/api/status')return json(res,{...doctor(),job});
      if(req.method==='GET'&&pathname==='/api/skills')return json(res,JSON.parse(readFileSync(path.join(root,'skills-inventory.json'),'utf8')));
      if(req.method==='POST'&&pathname==='/api/run'){
        const origin=req.headers.origin;if(origin&&![`http://127.0.0.1:${config.port}`,`http://localhost:${config.port}`].includes(origin))return json(res,{error:'Origin denied'},403);
        if(req.headers['x-workbench-token']!==token)return json(res,{error:'Token missing'},403);
        let text='';for await(const chunk of req){text+=chunk;if(text.length>2048)return json(res,{error:'Too large'},413);}
        const {action,engine}=JSON.parse(text);if(!['preview','check','render'].includes(action)||!['remotion','hyperframes'].includes(engine))return json(res,{error:'Unsupported operation'},400);
        if(job?.status==='running')return json(res,{error:'已有任务正在运行'},409);
        job={action,engine,status:'running',startedAt:new Date().toISOString()};
        perform(action,engine).then(result=>{job={...job,status:'done',result};}).catch(error=>{job={...job,status:'failed',error:error.message};});
        return json(res,{accepted:true});
      }
      if(req.method!=='GET'){res.writeHead(405);return res.end();}
      if(pathname==='/media/integration-demo.mp4')return sendFile(req,res,path.join(root,'exports/integration-demo.mp4'),'video/mp4');
      if(pathname==='/media/remotion-demo.mp4')return sendFile(req,res,path.join(remotion,'exports/project-launch.mp4'),'video/mp4');
      if(pathname==='/style-reference.jpg')return sendFile(req,res,path.resolve(root,'../skills/video-workbench/assets/latest-style.jpg'),'image/jpeg');
      if(pathname==='/poster.png')return sendFile(req,res,existsSync(path.join(root,'exports/integration-poster.png'))?path.join(root,'exports/integration-poster.png'):path.join(remotion,'exports/poster.png'),'image/png');
      if(pathname==='/'){const html=readFileSync(path.join(root,'web/index.html'),'utf8').replace('__TOKEN__',token);res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});return res.end(html);}
      res.writeHead(404);res.end('Not found');
    }catch(error){json(res,{error:error.message},500);}
  });
  server.listen(config.port,'127.0.0.1',()=>console.log(`Video Workbench http://127.0.0.1:${config.port}`));
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const [command='start',engine]=process.argv.slice(2);
  try{
    if(command==='serve')await serve();
    else if(command==='start')await start();
    else if(command==='doctor')console.log(JSON.stringify(doctor(),null,2));
    else if(command==='stage')console.log(JSON.stringify(await stage(),null,2));
    else console.log(JSON.stringify(await perform(command,engine),null,2));
  }catch(error){console.error(error.message);process.exitCode=1;}
}
