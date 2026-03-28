import React from "react";
import { Composition } from "remotion";
import { DailyMarketWrap } from "./DailyMarketWrap";
import { ProductDemoWalkthrough } from "./ProductDemoWalkthrough";
import demoSamplePayload from "./demoSamplePayload";
import samplePayload from "./samplePayload";

export const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="DailyMarketWrap"
        component={DailyMarketWrap}
        durationInFrames={samplePayload.duration_in_frames}
        fps={samplePayload.fps}
        width={samplePayload.width}
        height={samplePayload.height}
        defaultProps={{ payload: samplePayload }}
      />
      <Composition
        id="ProductDemoWalkthrough"
        component={ProductDemoWalkthrough}
        durationInFrames={demoSamplePayload.duration_in_frames}
        fps={demoSamplePayload.fps}
        width={demoSamplePayload.width}
        height={demoSamplePayload.height}
        defaultProps={{ payload: demoSamplePayload }}
      />
    </>
  );
};
