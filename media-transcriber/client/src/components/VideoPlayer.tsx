import { forwardRef } from 'react';

interface Props {
  src: string;
  isVideo: boolean;
}

const VideoPlayer = forwardRef<HTMLVideoElement, Props>(({ src, isVideo }, ref) => {
  if (!isVideo) {
    return (
      <div className="p-4 bg-dark-surface">
        <audio ref={ref as any} src={src} controls className="w-full" />
      </div>
    );
  }

  return (
    <div className="relative bg-black max-h-[300px] flex items-center justify-center">
      <video
        ref={ref}
        src={src}
        controls
        className="max-h-[300px] w-auto"
      />
    </div>
  );
});

VideoPlayer.displayName = 'VideoPlayer';

export default VideoPlayer;
