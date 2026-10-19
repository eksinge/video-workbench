import {Composition, Folder} from 'remotion';
import {ProjectLaunch} from './ProjectLaunch';
import {launchSchema} from './content';
import {CodexIntro, CodexOpening, CodexBuild, CodexClosing} from './CodexIntro';
import {LyricBackgroundDemo} from './LyricBackgroundDemo';

export const RemotionRoot = () => (
  <>
  <Composition id="LyricBackgroundDemo" component={LyricBackgroundDemo} width={1920} height={1080} fps={30} durationInFrames={2100}/>
  <Composition id="CodexIntro" component={CodexIntro} width={1920} height={1080} fps={30} durationInFrames={300}/>
  <Folder name="Codex-Scenes">
    <Composition id="CodexOpening" component={CodexOpening} width={1920} height={1080} fps={30} durationInFrames={90} defaultProps={{style:{backgroundColor:'#F0EFE8'}}}/>
    <Composition id="CodexBuild" component={CodexBuild} width={1920} height={1080} fps={30} durationInFrames={120} defaultProps={{style:{backgroundColor:'#161A19'}}}/>
    <Composition id="CodexClosing" component={CodexClosing} width={1920} height={1080} fps={30} durationInFrames={90} defaultProps={{style:{backgroundColor:'#FF7954'}}}/>
  </Folder>
  <Composition
    id="ProjectLaunch"
    component={ProjectLaunch}
    schema={launchSchema}
    defaultProps={{
      projectName: 'NEXT',
      eyebrow: '为你的下一个作品而来',
      headlineLine1: '让好想法',
      headlineLine2: '成为好作品。',
      description: '从一个灵感，到一次正式发布。',
      featureOne: '更快开始',
      featureTwo: '更少重复',
      featureThree: '持续创造',
      closingTitle: '你的下一个作品',
      callToAction: '现在，开始。',
      footer: 'MAKE SOMETHING THAT MATTERS.',
      accent: '#C8FA64',
      music: true,
    }}
    width={1920}
    height={1080}
    fps={30}
    durationInFrames={450}
  />
  </>
);
