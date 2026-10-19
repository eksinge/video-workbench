import type {CSSProperties, ReactNode} from 'react';
import {Audio} from '@remotion/media';
import {AbsoluteFill, Easing, interpolate, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import type {LaunchProps} from './content';

const ink = '#161815';
const paper = '#F3F1EB';
const font = '"Microsoft YaHei", "PingFang SC", sans-serif';
const mono = '"Consolas", monospace';
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
const rise = (frame: number, delay = 0) => spring({frame: frame - delay, fps: 30, config: {damping: 22, stiffness: 140}});
const reveal = (frame: number, start: number, length = 22) => interpolate(frame, [start, start + length], [0, 1], {...clamp, easing: Easing.out(Easing.cubic)});

const Arrow = ({size = 54, color = ink}: {size?: number; color?: string}) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
    <path d="M12 32H51M34 14L52 32L34 50" stroke={color} strokeWidth="4.5" strokeLinecap="square"/>
  </svg>
);

const Mark = ({accent, size = 52}: {accent: string; size?: number}) => (
  <div style={{width: size, height: size, background: accent, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: 'rotate(-8deg)'}}>
    <svg width={size * 0.65} height={size * 0.65} viewBox="0 0 64 64"><path d="M13 51V13H25L41 36V13H51V51H40L23 27V51Z" fill={ink}/></svg>
  </div>
);

const Topline = ({p, dark = false}: {p: LaunchProps; dark?: boolean}) => (
  <div style={{position: 'absolute', left: 104, right: 104, top: 68, display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: dark ? paper : ink}}>
    <div style={{display: 'flex', gap: 20, alignItems: 'center'}}><Mark accent={p.accent}/><span style={{fontSize: 36, fontWeight: 800, letterSpacing: -1}}>{p.projectName}</span></div>
    <div style={{fontFamily: mono, fontSize: 20, letterSpacing: 4}}>A NEW BEGINNING <span style={{color: dark ? p.accent : '#777B70'}}>↗</span></div>
  </div>
);

const Footer = ({p, number, dark = false}: {p: LaunchProps; number: string; dark?: boolean}) => (
  <div style={{position: 'absolute', left: 104, right: 104, bottom: 54, color: dark ? '#A5A99E' : '#6C7165', fontFamily: mono, fontSize: 18, display: 'flex', justifyContent: 'space-between', letterSpacing: 2}}>
    <span>{p.footer}</span><span>{number} / 03</span>
  </div>
);

const AnimatedLine = ({children, frame, delay, style}: {children: ReactNode; frame: number; delay: number; style?: CSSProperties}) => (
  <div style={{overflow: 'hidden', paddingBottom: 12, marginBottom: -12}}>
    <div style={{transform: `translateY(${(1 - reveal(frame, delay, 28)) * 115}%)`, ...style}}>{children}</div>
  </div>
);

const Intro = ({p}: {p: LaunchProps}) => {
  const frame = useCurrentFrame();
  const appear = rise(frame, 10);
  const exit = reveal(frame, 134, 18);
  return (
    <AbsoluteFill style={{background: paper, color: ink, transform: `translateY(${-exit * 110}px)`, opacity: 1 - exit}}>
      <div style={{position: 'absolute', inset: 0, backgroundImage: 'linear-gradient(#191C1610 1px, transparent 1px), linear-gradient(90deg, #191C1610 1px, transparent 1px)', backgroundSize: '80px 80px', maskImage: 'linear-gradient(90deg,transparent 40%,black)'}}/>
      <Topline p={p}/>
      <div style={{position: 'absolute', left: 104, top: 246, zIndex: 2}}>
        <div style={{fontSize: 24, marginBottom: 34, letterSpacing: 6, opacity: reveal(frame, 4)}}><span style={{display: 'inline-block', width: 10, height: 10, borderRadius: 10, marginRight: 18, background: ink}}/>{p.eyebrow}</div>
        <div style={{fontSize: 138, fontWeight: 900, lineHeight: 1.28, letterSpacing: -8}}>
          <AnimatedLine frame={frame} delay={10}>{p.headlineLine1}</AnimatedLine>
          <AnimatedLine frame={frame} delay={20}><span style={{position: 'relative'}}><span style={{position: 'absolute', left: -8, right: -18, bottom: 7, height: 42, background: p.accent, transform: `scaleX(${reveal(frame, 36, 28)})`, transformOrigin: 'left'}}/><span style={{position: 'relative'}}>{p.headlineLine2}</span></span></AnimatedLine>
        </div>
        <div style={{fontSize: 29, marginTop: 38, color: '#6C7165', opacity: reveal(frame, 42), transform: `translateY(${(1 - reveal(frame, 42)) * 20}px)`}}>{p.description}</div>
      </div>
      <div style={{position: 'absolute', right: 100, top: 265, width: 510, height: 510, transform: `translateY(${(1 - appear) * 100 + Math.sin(frame / 32) * 10}px) rotate(${12 - appear * 4}deg) scale(${0.7 + appear * 0.3})`, opacity: appear}}>
        <div style={{position: 'absolute', inset: 30, border: '1px solid #B9BEB0', borderRadius: '50%', transform: 'scale(1.2)'}}/>
        <div style={{position: 'absolute', inset: 0, background: ink, borderRadius: 38, boxShadow: '20px 35px 60px #16181525', padding: 42}}>
          <div style={{display: 'flex', justifyContent: 'space-between', color: '#969E8A', fontFamily: mono, fontSize: 18}}><span>IDEA → REALITY</span><span>001</span></div>
          <div style={{height: 250, display: 'flex', alignItems: 'center', justifyContent: 'center'}}><div style={{transform: `rotate(${-frame / 8}deg)`}}><svg width="230" height="230" viewBox="0 0 240 240"><path d="M120 12L139 80L200 40L160 101L228 120L160 139L200 200L139 160L120 228L101 160L40 200L80 139L12 120L80 101L40 40L101 80Z" fill={p.accent}/></svg></div></div>
          <div style={{fontSize: 48, fontWeight: 800, color: paper, letterSpacing: -2}}>Made to move.</div>
          <div style={{height: 4, background: '#3C4235', marginTop: 24}}><div style={{height: 4, background: p.accent, width: `${reveal(frame, 35, 80) * 100}%`}}/></div>
        </div>
        <div style={{position: 'absolute', right: -26, bottom: -22, width: 108, height: 108, background: p.accent, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: 'rotate(-8deg)'}}><Arrow/></div>
      </div>
      <Footer p={p} number="01"/>
    </AbsoluteFill>
  );
};

const Features = ({p}: {p: LaunchProps}) => {
  const frame = useCurrentFrame();
  const exit = reveal(frame, 134, 18);
  const features = [p.featureOne, p.featureTwo, p.featureThree];
  return (
    <AbsoluteFill style={{background: ink, color: paper, opacity: 1 - exit}}>
      <Topline p={p} dark/>
      <div style={{position: 'absolute', left: 104, top: 228}}>
        <AnimatedLine frame={frame} delay={8} style={{fontFamily: mono, color: p.accent, fontSize: 22, letterSpacing: 5}}>LESS FRICTION. MORE FLOW.</AnimatedLine>
        <AnimatedLine frame={frame} delay={16} style={{fontSize: 92, fontWeight: 800, marginTop: 24, letterSpacing: -4}}>好用，发生在每一步。</AnimatedLine>
      </div>
      <div style={{position: 'absolute', left: 104, right: 104, top: 464, display: 'flex'}}>
        {features.map((label, i) => {
          const v = rise(frame, 30 + i * 12);
          return <div key={i} style={{flex: 1, height: 326, borderTop: '1px solid #51574A', borderRight: i < 2 ? '1px solid #51574A' : undefined, padding: '34px 40px', paddingLeft: i === 0 ? 0 : 40, opacity: v, transform: `translateY(${(1 - v) * 60}px)`}}>
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 56}}><span style={{fontFamily: mono, color: '#929A86', fontSize: 22}}>0{i + 1}</span><div style={{width: 58, height: 58, borderRadius: i === 1 ? 8 : '50%', border: `2px solid ${p.accent}`, display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `rotate(${i === 1 ? 45 : 0}deg)`}}><div style={{width: 18 + Math.sin(frame / 14 + i) * 3, height: 18, background: p.accent, borderRadius: i === 1 ? 2 : '50%'}}/></div></div>
            <div style={{fontSize: 58, fontWeight: 700, letterSpacing: -2}}>{label}</div>
            <div style={{fontFamily: mono, color: '#8F9883', fontSize: 19, marginTop: 20, letterSpacing: 2}}>{['START WITH AN IDEA', 'BUILD YOUR OWN FLOW', 'MAKE IT HAPPEN'][i]}</div>
          </div>;
        })}
      </div>
      <div style={{position: 'absolute', left: 104, right: 104, top: 834, height: 3, background: '#353B2E'}}><div style={{height: 3, width: `${reveal(frame, 40, 90) * 100}%`, background: p.accent}}/></div>
      <Footer p={p} number="02" dark/>
    </AbsoluteFill>
  );
};

const Closing = ({p}: {p: LaunchProps}) => {
  const frame = useCurrentFrame();
  const v = rise(frame, 8);
  return (
    <AbsoluteFill style={{background: p.accent, color: ink}}>
      <div style={{position: 'absolute', right: -220, top: -240, width: 1050, height: 1050, border: '1px solid #16181525', borderRadius: '50%', transform: `scale(${0.8 + reveal(frame, 0, 100) * 0.2})`}}/>
      <div style={{position: 'absolute', right: -70, top: -90, width: 750, height: 750, border: '1px solid #16181525', borderRadius: '50%'}}/>
      <Topline p={p}/>
      <div style={{position: 'absolute', top: 270, left: 104, right: 104}}>
        <AnimatedLine frame={frame} delay={8} style={{fontSize: 40, letterSpacing: 3}}>{p.closingTitle}</AnimatedLine>
        <AnimatedLine frame={frame} delay={18} style={{fontSize: 166, fontWeight: 900, letterSpacing: -10, lineHeight: 1.5}}>{p.callToAction}</AnimatedLine>
        <div style={{display: 'inline-flex', alignItems: 'center', gap: 50, background: ink, color: paper, padding: '24px 34px', borderRadius: 6, fontSize: 29, fontWeight: 700, opacity: reveal(frame, 38), transform: `translateY(${(1 - reveal(frame, 38)) * 30}px)`}}><span>{p.projectName}</span><Arrow size={38} color={p.accent}/></div>
      </div>
      <div style={{position: 'absolute', right: 140, bottom: 190, width: 184, height: 184, border: '2px solid #161815', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', transform: `rotate(${-40 + v * 40}deg) scale(${v})`}}><Arrow size={92}/></div>
      <Footer p={p} number="03"/>
    </AbsoluteFill>
  );
};

export const ProjectLaunch = (p: LaunchProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{fontFamily: font, background: ink, overflow: 'hidden'}}>
      <Sequence durationInFrames={5 * fps + 2} premountFor={fps} name="01 · 开场"><Intro p={p}/></Sequence>
      <Sequence from={5 * fps} durationInFrames={5 * fps + 2} premountFor={fps} name="02 · 三个卖点"><Features p={p}/></Sequence>
      <Sequence from={10 * fps} durationInFrames={5 * fps} premountFor={fps} name="03 · 正式发布"><Closing p={p}/></Sequence>
      <div style={{position: 'absolute', left: 0, bottom: 0, height: 5, width: `${(frame / 449) * 100}%`, background: frame < 300 ? p.accent : ink}}/>
      {p.music ? <Audio src={staticFile('launch.wav')} volume={0.65}/> : null}
    </AbsoluteFill>
  );
};
