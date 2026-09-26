import React, { useState, useEffect, useRef } from 'react';

export function Preloader({ onComplete }) {
  const [isFading, setIsFading] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const videoRef = useRef(null);
  const safetyTimeoutRef = useRef(null);

  const finishPreloader = () => {
    if (isFading || isDone) return;
    setIsFading(true);
    setTimeout(() => {
      setIsDone(true);
      onComplete?.();
    }, 600);
  };

  useEffect(() => {
    const video = videoRef.current;
    if (video) {
      // Force play programmatically with muted to ensure autoplay policies are satisfied
      video.muted = true;
      video.play().catch((err) => {
        console.warn('Autoplay prevented or video load error:', err);
      });
    }

    // Maximum safety timeout (6 seconds) to prevent app blockage under any circumstance
    safetyTimeoutRef.current = setTimeout(() => {
      finishPreloader();
    }, 6000);

    return () => {
      if (safetyTimeoutRef.current) clearTimeout(safetyTimeoutRef.current);
    };
  }, []);

  const handleEnded = () => {
    finishPreloader();
  };

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video && video.duration > 0) {
      // Initiate smooth fade-out 0.25s before end for seamless transition
      if (video.currentTime >= video.duration - 0.25) {
        finishPreloader();
      }
    }
  };

  const handleError = (e) => {
    console.error('Video preloader error:', e);
    // On error, immediately fade out gracefully
    finishPreloader();
  };

  if (isDone) return null;

  return (
    <div
      className={`preloader-video-overlay ${isFading ? 'preloader-video-fade-out' : ''}`}
      aria-label="Loading Application"
      role="status"
    >
      <video
        ref={videoRef}
        className="preloader-video-element"
        autoPlay
        muted
        playsInline
        preload="auto"
        onEnded={handleEnded}
        onTimeUpdate={handleTimeUpdate}
        onError={handleError}
      >
        <source src="/preloader.mp4" type="video/mp4" />
      </video>

      {/* Subtle skip control */}
      <button
        type="button"
        onClick={finishPreloader}
        className="preloader-skip-btn"
        title="Skip intro"
      >
        Skip ✕
      </button>
    </div>
  );
}

export default Preloader;
