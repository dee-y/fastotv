#pragma once

#include "ffmpeg_config.h"

extern "C" {
#include <libavcodec/avcodec.h>
#include <SDL2/SDL_render.h>
}

#include <common/macros.h>

namespace core {

/* Common struct for handling all types of decoded data and allocated render buffers. */
struct VideoFrame {
  VideoFrame();
  ~VideoFrame();
  void ClearFrame();

  AVFrame* frame;
  int serial;
  double pts;      /* presentation timestamp for the frame */
  double duration; /* estimated duration of the frame */
  int64_t pos;     /* byte position of the frame in the input file */
  SDL_Texture* bmp;
  int allocated;
  int width;
  int height;
  int format;
  AVRational sar;
  int uploaded;
  int flip_v;

 private:
  DISALLOW_COPY_AND_ASSIGN(VideoFrame);
};

}  // namespace core
