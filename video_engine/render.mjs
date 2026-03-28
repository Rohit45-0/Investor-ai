import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { bundle } from "@remotion/bundler";
import { getCompositions, renderMedia } from "@remotion/renderer";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const parseArgs = () => {
  const args = process.argv.slice(2);
  const options = {
    payload: null,
    api: null,
    out: null,
    scale: 1,
    preview: false,
    composition: "DailyMarketWrap",
  };

  for (let index = 0; index < args.length; index += 1) {
    const value = args[index];
    if (value === "--payload") {
      options.payload = args[index + 1];
      index += 1;
    } else if (value === "--api") {
      options.api = args[index + 1];
      index += 1;
    } else if (value === "--out") {
      options.out = args[index + 1];
      index += 1;
    } else if (value === "--scale") {
      options.scale = Number(args[index + 1] || 1);
      index += 1;
    } else if (value === "--preview") {
      options.preview = true;
    } else if (value === "--composition") {
      options.composition = args[index + 1] || options.composition;
      index += 1;
    }
  }

  if (!options.out) {
    const filename = options.composition === "ProductDemoWalkthrough" ? "product_demo.mp4" : "daily_market_wrap.mp4";
    options.out = path.join(__dirname, "out", filename);
  }

  return options;
};

const loadPayload = async (options) => {
  if (options.api) {
    const response = await fetch(options.api);
    if (!response.ok) {
      throw new Error(`Could not fetch payload from ${options.api}: ${response.status}`);
    }
    return response.json();
  }

  if (options.payload) {
    const text = await readFile(path.resolve(options.payload), "utf8");
    return JSON.parse(text);
  }

  const sampleFile = options.composition === "ProductDemoWalkthrough" ? "demoSamplePayload.js" : "samplePayload.js";
  const sampleModule = await import(pathToFileURL(path.join(__dirname, "src", sampleFile)).href);
  return sampleModule.default;
};

const render = async () => {
  const options = parseArgs();
  const payload = await loadPayload(options);
  const entryPoint = path.join(__dirname, "src", "index.jsx");
  console.log(`Bundling Remotion project from ${entryPoint}`);
  const bundled = await bundle({
    entryPoint,
    onProgress: () => undefined,
  });

  const inputProps = { payload };
  console.log("Loading compositions");
  const compositions = await getCompositions(bundled, { inputProps });
  const composition = compositions.find((item) => item.id === options.composition);
  if (!composition) {
    throw new Error(`Could not find the ${options.composition} composition.`);
  }
  console.log(
    `Selected composition ${composition.id} (${composition.width}x${composition.height}, ${composition.durationInFrames} frames)`,
  );

  let lastLoggedFrame = -1;
  const frameRange = options.preview ? [0, Math.min(179, composition.durationInFrames - 1)] : null;

  await renderMedia({
    codec: "h264",
    composition,
    serveUrl: bundled,
    outputLocation: path.resolve(options.out),
    inputProps,
    scale: options.preview ? 0.5 : options.scale,
    frameRange,
    concurrency: 2,
    logLevel: "info",
    onStart: ({ frameCount }) => {
      console.log(`Starting render for ${frameCount} frames`);
    },
    onProgress: (progress) => {
      if (
        progress.renderedFrames === lastLoggedFrame ||
        (progress.renderedFrames !== 0 && progress.renderedFrames % 30 !== 0 && progress.progress < 0.999)
      ) {
        return;
      }
      lastLoggedFrame = progress.renderedFrames;
      console.log(
        `Render ${Math.round(progress.progress * 100)}% | rendered ${progress.renderedFrames} | encoded ${progress.encodedFrames} | stage ${progress.stitchStage}`,
      );
    },
  });

  console.log(`Rendered ${path.resolve(options.out)}`);
};

render().catch((error) => {
  console.error(error);
  process.exit(1);
});
