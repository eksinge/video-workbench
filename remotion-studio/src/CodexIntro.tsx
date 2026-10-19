import {Audio} from '@remotion/media';
import {AbsoluteFill, Easing, Interactive, interpolate, staticFile, Track, useCurrentFrame, useVideoConfig} from 'remotion';

const ink = '#161A19';
const cream = '#F0EFE8';
const mint = '#A9F1D0';
const orange = '#FF7954';
const font = '"Microsoft YaHei", "Arial", sans-serif';
const mono = '"Consolas", monospace';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const Frame = ({dark = false}: {dark?: boolean}) => <>
  <div style={{position:'absolute',left:112,right:112,top:64,display:'flex',justifyContent:'space-between',fontFamily:mono,fontSize:25,letterSpacing:3,color:dark?cream:ink}}>
    <span>OpenAI / Codex</span><span>IDEA → CODE → BUILD</span>
  </div>
  <div style={{position:'absolute',left:112,right:112,bottom:60,borderTop:`1px solid ${dark?'#49514D':'#A2A59B'}`,paddingTop:22,display:'flex',justifyContent:'space-between',color:dark?'#B3BDB6':'#555D57',fontSize:22,fontFamily:mono}}>
    <span>YOUR AI CODING PARTNER</span><span>从想法，到作品。</span>
  </div>
</>;

const OpeningInner = () => {
  const f = useCurrentFrame(); const {fps} = useVideoConfig();
  return <>
    <Frame/>
    <div style={{position:'absolute',left:106,top:209,fontFamily:font,color:ink}}>
      <div style={{fontSize:36,letterSpacing:7,opacity:interpolate(f,[0,.4*fps],[0,1],clamp)}}>认识你的 AI 编程搭档</div>
      <div style={{fontFamily:mono,fontSize:260,fontWeight:700,letterSpacing:-19,lineHeight:1.4,translate:interpolate(f,[0,.6*fps],['0px 85px','0px 0px'],{...clamp,easing:Easing.out(Easing.cubic)}),opacity:interpolate(f,[0,.35*fps],[0,1],clamp)}}>Codex<span style={{color:orange}}>_</span></div>
      <div style={{fontSize:56,fontWeight:600,marginTop:10,opacity:interpolate(f,[.5*fps,.9*fps],[0,1],clamp)}}>一句话，开启下一次创造。</div>
    </div>
    <div style={{position:'absolute',right:140,top:308,width:290,height:290,border:`2px solid ${ink}`,borderRadius:44,rotate:interpolate(f,[0,3*fps],['-12deg','8deg'],clamp),scale:interpolate(f,[0,.7*fps],[.5,1],{...clamp,easing:Easing.out(Easing.cubic)}),background:mint,display:'flex',justifyContent:'center',alignItems:'center',fontSize:140,fontFamily:mono,fontWeight:700}}>{'>'}<span style={{color:orange}}>_</span></div>
    <div style={{position:'absolute',left:0,right:0,bottom:0,height:12,background:orange,scale: `${interpolate(f,[0,3*fps],[0,1],clamp)} 1`,transformOrigin:'left'}}/>
  </>;
};
export const CodexOpening = Interactive.create({Component:OpeningInner,layout:'absolute-fill'});

const BuildInner = () => {
  const f = useCurrentFrame(); const {fps} = useVideoConfig();
  const prompt = '帮我把这个想法，做成一个能用的应用。';
  const typed = prompt.slice(0,Math.min(prompt.length,Math.floor(f/1.25)));
  return <>
    <Frame dark/>
    <div style={{position:'absolute',left:112,top:228,color:cream,fontFamily:font}}>
      <div style={{fontFamily:mono,fontSize:25,color:mint,letterSpacing:5}}>FROM PROMPT TO PROGRESS</div>
      <div style={{fontSize:98,lineHeight:1.3,fontWeight:700,marginTop:40}}>写代码。<br/>修问题。<br/><span style={{color:mint}}>跑验证。</span></div>
    </div>
    <div style={{position:'absolute',left:850,right:112,top:219,height:574,border:'1px solid #48524C',background:'#202723',borderRadius:24,overflow:'hidden',fontFamily:mono,translate:interpolate(f,[0,.5*fps],['100px 0px','0px 0px'],{...clamp,easing:Easing.out(Easing.cubic)})}}>
      <div style={{height:68,borderBottom:'1px solid #48524C',display:'flex',alignItems:'center',padding:'0 28px',gap:12}}><span style={{width:14,height:14,borderRadius:20,background:orange}}/><span style={{width:14,height:14,borderRadius:20,background:'#E6C56E'}}/><span style={{width:14,height:14,borderRadius:20,background:mint}}/><span style={{marginLeft:24,fontSize:23,color:'#B3BDB6'}}>codex / workspace</span></div>
      <div style={{padding:'34px 32px',color:cream,fontFamily:font,fontSize:29,lineHeight:1.7}}><span style={{color:mint}}>❯ </span>{typed}<span style={{color:mint}}>▌</span></div>
      <div style={{padding:'10px 32px',fontSize:30,lineHeight:2.25}}>
        <div style={{color:cream,opacity:interpolate(f,[.9*fps,1.2*fps],[0,1],clamp)}}><span style={{color:mint}}>✓</span> 理解项目，拆解任务</div>
        <div style={{color:cream,opacity:interpolate(f,[1.6*fps,1.9*fps],[0,1],clamp)}}><span style={{color:mint}}>✓</span> 编辑代码，解决问题</div>
        <div style={{color:cream,opacity:interpolate(f,[2.3*fps,2.6*fps],[0,1],clamp)}}><span style={{color:mint}}>✓</span> 运行检查，交付结果</div>
      </div>
      <div style={{position:'absolute',bottom:22,right:28,color:'#9CA89F',fontSize:20}}>工作流示意</div>
    </div>
    <div style={{position:'absolute',left:850,right:112,top:832,fontFamily:font,fontSize:32,color:mint,opacity:interpolate(f,[2.9*fps,3.2*fps],[0,1],clamp)}}>从读懂项目，到一起完成它。</div>
  </>;
};
export const CodexBuild = Interactive.create({Component:BuildInner,layout:'absolute-fill'});

const ClosingInner = () => {
  const f=useCurrentFrame();const {fps}=useVideoConfig();
  return <>
    <Frame/>
    <div style={{position:'absolute',right:-200,top:140,width:850,height:850,border:`2px solid ${ink}30`,borderRadius:'50%',scale:interpolate(f,[0,3*fps],[.8,1.15],clamp)}}/>
    <div style={{position:'absolute',left:112,top:242,color:ink,fontFamily:font}}>
      <div style={{fontSize:40,letterSpacing:5,opacity:interpolate(f,[0,.4*fps],[0,1],clamp)}}>你来定义方向</div>
      <div style={{fontSize:138,letterSpacing:-6,fontWeight:800,lineHeight:1.45,marginTop:20,translate:interpolate(f,[0,.6*fps],['0px 65px','0px 0px'],{...clamp,easing:Easing.out(Easing.cubic)})}}>让 Codex<br/>陪你把想法做出来。</div>
      <div style={{display:'inline-flex',alignItems:'center',gap:55,marginTop:36,padding:'20px 32px',background:ink,color:cream,borderRadius:8,fontFamily:mono,fontSize:36,opacity:interpolate(f,[.6*fps,1*fps],[0,1],clamp)}}>Codex <span style={{color:mint}}>→</span></div>
    </div>
  </>;
};
export const CodexClosing = Interactive.create({Component:ClosingInner,layout:'absolute-fill'});

export const CodexIntro = () => {
  const f=useCurrentFrame();const {fps}=useVideoConfig();
  return <AbsoluteFill style={{background:ink,overflow:'hidden'}}>
    <Track name="Codex · 十秒介绍">
      <CodexOpening name="01 · 认识 Codex" durationInFrames={3*fps} style={{backgroundColor:cream}}/>
      <CodexBuild name="02 · 编程工作流" from={3*fps} durationInFrames={4*fps} style={{backgroundColor:ink}}/>
      <CodexClosing name="03 · 把想法做出来" from={7*fps} durationInFrames={3*fps} style={{backgroundColor:orange}}/>
    </Track>
    <Audio name="本地合成器配乐" src={staticFile('launch.wav')} durationInFrames={10*fps} volume={interpolate(f,[0,.25*fps,9.3*fps,10*fps],[0,.7,.7,0],clamp)}/>
  </AbsoluteFill>;
};
