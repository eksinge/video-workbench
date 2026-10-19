import React from 'react';
import {AbsoluteFill,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';

export const LyricBackgroundDemo: React.FC = () => {
  const frame=useCurrentFrame();
  const {fps}=useVideoConfig();
  const t=frame/fps;
  const angle=Math.sin(t*.35)*2;
  const scale=1+Math.sin(t*.9)*.025;
  return <AbsoluteFill style={{background:'#111111',overflow:'hidden'}}>
    <svg viewBox="0 0 1920 1080" width="100%" height="100%">
      <path d="M0 0 H1920 V32 L1850 21 1780 36 1700 20 1620 35 1540 21 1460 36 1380 20 1300 35 1220 20 1140 35 1060 21 980 35 900 21 820 36 740 21 660 35 580 21 500 36 420 21 340 35 260 21 180 36 100 20 0 34Z" fill="#F0ECE5"/>
      <path d="M0 1080 H1920 V1048 L1850 1060 1780 1044 1700 1060 1620 1045 1540 1061 1460 1044 1380 1060 1300 1045 1220 1060 1140 1045 1060 1060 980 1045 900 1060 820 1044 740 1060 660 1045 580 1060 500 1044 420 1060 340 1045 260 1060 180 1044 100 1060 0 1046Z" fill="#F0ECE5"/>
      <path d="M110 115H1810" stroke="#F0ECE5" strokeOpacity=".22" strokeWidth="2"/>
      <g transform={`translate(870 540) rotate(${angle}) scale(${scale})`}>
        <circle r="350" stroke="#E85D26" strokeWidth="2" fill="none" opacity=".5"/>
        <circle r="390" stroke="#F0ECE5" strokeWidth="1" fill="none" opacity=".13"/>
        <path d="M-600 -5 L-445 -142 -380 -196 -318 -176 -243 -249 -165 -213 -74 -260 22 -228 116 -256 196 -206 284 -232 355 -161 430 -174 600 -5 433 160 353 144 278 218 194 195 104 247 19 223 -78 250 -163 211 -247 236 -323 171 -388 190 -458 120Z" fill="#F0ECE5"/>
        <path d="M-485 -4 Q-4 -345 485 -4 Q5 340 -485 -4Z" fill="#111111"/>
        <path d="M-105 -243 Q25 -288 133 -147 L105 218 Q-35 286 -137 139Z" fill="#E85D26"/>
        <ellipse cx="0" cy="0" rx="47" ry="180" fill="#111111"/>
        <circle cx="81" cy="-112" r="25" fill="#F0ECE5"/>
      </g>
      <path d="M110 933H310" stroke="#E85D26" strokeOpacity=".5" strokeWidth="3"/>
      <text x="110" y="994" fill="#F0ECE5" fontFamily="monospace" fontSize="25" letterSpacing="4">YOUR SONG · LOCAL MV</text>
    </svg>
    <AbsoluteFill style={{pointerEvents:'none',opacity:.12,mixBlendMode:'screen',backgroundImage:`url(${staticFile('grain.png')})`,backgroundPosition:`${frame%5*3}px ${frame%7*2}px`}}/>
  </AbsoluteFill>;
};
