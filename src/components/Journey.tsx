import { lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  AnimatePresence,
  motion,
  useMotionValueEvent,
  useMotionValue,
  useTransform,
  useScroll,
} from "motion/react";
import { ArrowDown, Pause, Play } from "lucide-react";

const Makerspace = lazy(() => import("./Makerspace"));
const stops = [
  { name: "Welcome", sentence: "" },
  { name: "Imagine", sentence: "Turn a rough idea into a plan." },
  { name: "Understand", sentence: "Work out the physics before you build." },
  { name: "Design", sentence: "Shape every detail with CAD and CAM." },
  {
    name: "Source",
    sentence: "Find the lowest-cost parts that fit your design.",
  },
  { name: "Build", sentence: "Bring it all together in a working prototype." },
];
const lastStop = stops.length - 1;
const stationAt = (value: number) =>
  [0.1, 0.3, 0.52, 0.7, 0.9].filter((boundary) => value >= boundary).length;

export default function Journey({ reduced }: { reduced: boolean }) {
  const target = useRef<HTMLElement>(null);
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const [sceneReady, setSceneReady] = useState(false);
  const renderedProgress = useMotionValue(0);
  // Let the image lead while moving around the board into fabrication.
  const captionOpacity = useTransform(
    renderedProgress,
    [0, 0.43, 0.48, 0.52, 0.58, 1],
    [1, 1, 0, 0, 1, 1],
  );
  const { scrollYProgress } = useScroll({
    target,
    offset: ["start start", "end end"],
  });
  useMotionValueEvent(scrollYProgress, "change", (value) => {
    if (reduced || !sceneReady) setActive(stationAt(value));
  });
  useMotionValueEvent(renderedProgress, "change", (value) => {
    if (!reduced && sceneReady) setActive(stationAt(value));
  });
  useEffect(() => {
    setActive(
      stationAt(
        reduced || !sceneReady ? scrollYProgress.get() : renderedProgress.get(),
      ),
    );
  }, [reduced, sceneReady, scrollYProgress, renderedProgress]);
  function goTo(index: number) {
    if (!target.current) return;
    const top = target.current.getBoundingClientRect().top + window.scrollY;
    window.scrollTo({
      top:
        top +
        ((target.current.offsetHeight - window.innerHeight) * index) / lastStop,
      behavior: reduced ? "instant" : "smooth",
    });
  }
  return (
    <section
      className="journey"
      id="workbench"
      ref={target}
      aria-label="Explore the Mechy makerspace"
    >
      <div className={`journey-sticky ${active === 0 ? "is-intro" : ""}`}>
        <Suspense
          fallback={
            <div className="scene-fallback">
              <img src="/makerspace-poster.webp" alt="Mechy makerspace" />
            </div>
          }
        >
          <Makerspace
            progress={scrollYProgress}
            renderedProgress={renderedProgress}
            onReadyChange={setSceneReady}
            reduced={reduced}
            paused={paused}
          />
        </Suspense>
        <div className="journey-veil" aria-hidden="true" />
        {active > 0 && (
          <div className="journey-topline">
            <a
              href="#workbench"
              onClick={(e) => {
                e.preventDefault();
                goTo(0);
              }}
            >
              mechy.
            </a>
            <a href="#pricing">Get the demo</a>
          </div>
        )}
        <motion.div
          style={{ opacity: reduced || !sceneReady ? 1 : captionOpacity }}
          className={`journey-copy ${active === 0 ? "journey-hero" : "journey-chapter"}`}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={active}
              initial={{ opacity: 0, y: reduced ? 0 : 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: reduced ? 0 : -12 }}
              transition={{ duration: reduced ? 0 : 0.25 }}
            >
              {active === 0 ? (
                <>
                  <h1>
                    mechy<span>.</span>
                  </h1>
                  <p>
                    An AI engineering workspace
                    <br />
                    for people who make things.
                  </p>
                  <button className="enter-workshop" onClick={() => goTo(1)}>
                    Step inside <ArrowDown size={15} />
                  </button>
                </>
              ) : (
                <h2>{stops[active].sentence}</h2>
              )}
            </motion.div>
          </AnimatePresence>
        </motion.div>
        <div className="journey-bottom">
          <nav className="journey-nav" aria-label="Workshop stops">
            {stops.map((stop, index) => (
              <button
                key={stop.name}
                onClick={() => goTo(index)}
                aria-current={active === index ? "step" : undefined}
              >
                {stop.name}
                <i />
              </button>
            ))}
          </nav>
          <button
            className="motion-toggle"
            onClick={() => setPaused(!paused)}
            aria-label={
              reduced
                ? "Motion disabled by system preference"
                : paused
                  ? "Resume journey motion"
                  : "Pause journey motion"
            }
            aria-pressed={paused || reduced}
            disabled={reduced}
          >
            {paused || reduced ? <Play size={14} /> : <Pause size={14} />}
          </button>
        </div>
        <motion.div
          className="journey-progress"
          style={{ scaleX: scrollYProgress }}
        />
      </div>
    </section>
  );
}
