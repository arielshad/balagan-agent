import React from 'react';
import {Composition, Still} from 'remotion';
import {Thumbnail} from './Thumbnail';
import {SlideProblem, SlideSolution, SlideArchitecture, SlideReport, SlideCode, SlideStress} from './GallerySlide';
import {DemoVideo} from './DemoVideo';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Thumbnail */}
      <Still id="thumbnail" component={Thumbnail} width={240} height={240} />

      {/* Gallery images */}
      <Still id="gallery-1-problem" component={SlideProblem} width={1270} height={760} />
      <Still id="gallery-2-solution" component={SlideSolution} width={1270} height={760} />
      <Still id="gallery-3-architecture" component={SlideArchitecture} width={1270} height={760} />
      <Still id="gallery-4-report" component={SlideReport} width={1270} height={760} />
      <Still id="gallery-5-code" component={SlideCode} width={1270} height={760} />
      <Still id="gallery-6-stress" component={SlideStress} width={1270} height={760} />

      {/* Demo video: 15fps × 40s = 600 frames */}
      <Composition
        id="demo-video"
        component={DemoVideo}
        durationInFrames={600}
        fps={15}
        width={1270}
        height={760}
      />
    </>
  );
};
