Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "dualeye_video_renderer.cpp"
text = path.read_text(encoding="utf-8")


def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"eye-look geometry patch expected exactly one {label} anchor, found {count}"
        )
    text = text.replace(old, new, 1)


replace_once(
    """void drawAnimalEye(GFXcanvas16 &canvas, bool leftEye, Rgb baseColor,
                   uint32_t now, bool errorState, bool menuState) {
""",
    """void drawStarPupil(GFXcanvas16 &canvas, int x, int y, int r,
                   uint16_t color) {
  canvas.fillTriangle(x, y - r, x - r / 3, y - r / 4,
                      x + r / 3, y - r / 4, color);
  canvas.fillTriangle(x, y + r, x - r / 3, y + r / 4,
                      x + r / 3, y + r / 4, color);
  canvas.fillTriangle(x - r, y, x - r / 4, y - r / 3,
                      x - r / 4, y + r / 3, color);
  canvas.fillTriangle(x + r, y, x + r / 4, y - r / 3,
                      x + r / 4, y + r / 3, color);
  canvas.fillCircle(x, y, max(2, r / 2), color);
}

void drawHeartPupil(GFXcanvas16 &canvas, int x, int y, int r,
                    uint16_t color) {
  const int lobe = max(3, r / 2);
  canvas.fillCircle(x - r / 3, y - r / 4, lobe, color);
  canvas.fillCircle(x + r / 3, y - r / 4, lobe, color);
  canvas.fillTriangle(x - r, y - r / 8, x + r, y - r / 8,
                      x, y + r, color);
}

void drawXPupil(GFXcanvas16 &canvas, int x, int y, int r,
                uint16_t color) {
  for (int offset = -2; offset <= 2; ++offset) {
    canvas.drawLine(x - r, y - r + offset, x + r, y + r + offset, color);
    canvas.drawLine(x + r, y - r + offset, x - r, y + r + offset, color);
  }
}

void drawStyledPupil(GFXcanvas16 &canvas, int x, int y, int irisR,
                     bool leftEye) {
  const uint16_t pupil = rgb565(1, 3, 4);
  const uint16_t catchlight = rgb565(245, 248, 241);
  const uint16_t catchlightDim = rgb565(183, 207, 202);
  const int shapeR = clampInt((int)(irisR * 0.58f), 8, 18);

  if (eqi(eyes.look, "heart")) {
    drawHeartPupil(canvas, x, y, shapeR, pupil);
  } else if (eqi(eyes.look, "star")) {
    drawStarPupil(canvas, x, y, shapeR, pupil);
  } else if (eqi(eyes.look, "x")) {
    drawXPupil(canvas, x, y, shapeR, pupil);
    return;
  } else if (eqi(eyes.look, "round")) {
    canvas.fillCircle(x, y, clampInt(irisR / 3, 5, 10), pupil);
  } else if (eqi(eyes.look, "sleepy")) {
    canvas.fillEllipse(x, y, clampInt(irisR / 2, 7, 13),
                       clampInt(irisR / 7, 2, 4), pupil);
  } else if (eqi(eyes.look, "slit")) {
    canvas.fillEllipse(x, y, clampInt(irisR / 7, 3, 5),
                       clampInt((int)(irisR * 0.76f), 11, 21), pupil);
  } else if (eqi(eyes.look, "angry")) {
    canvas.fillEllipse(x, y + 1, clampInt(irisR / 5, 4, 6),
                       clampInt((int)(irisR * 0.62f), 9, 18), pupil);
    canvas.drawLine(x - shapeR / 2, y - shapeR / 2,
                    x + shapeR / 2, y - shapeR / 4, pupil);
  } else {
    // Default cyber-koala pupil: tall animal slit with a small central core.
    canvas.fillEllipse(x, y, clampInt(irisR / 4, 4, 7),
                       clampInt((int)(irisR * 0.70f), 10, 19), pupil);
    canvas.fillCircle(x, y, 2, rgb565(20, 30, 32));
  }

  canvas.fillCircle(x + (leftEye ? 6 : -6), y - 8, 4, catchlight);
  canvas.fillCircle(x + (leftEye ? -4 : 4), y + 6, 2, catchlightDim);
}

void drawAnimalEye(GFXcanvas16 &canvas, bool leftEye, Rgb baseColor,
                   uint32_t now, bool errorState, bool menuState) {
""",
    "styled pupil helper insertion",
)

replace_once(
    """  // Koala-like vertical animal pupil with moist asymmetric catchlights.
  canvas.fillEllipse(kCenter + gazeX, eyeCy + gazeY,
                     clampInt(irisR / 4, 4, 7),
                     clampInt((int)(irisR * 0.70f), 10, 19),
                     rgb565(1, 3, 4));
  canvas.fillCircle(kCenter + gazeX + (leftEye ? 6 : -6),
                    eyeCy + gazeY - 8, 4, rgb565(245, 248, 241));
  canvas.fillCircle(kCenter + gazeX + (leftEye ? -4 : 4),
                    eyeCy + gazeY + 6, 2, rgb565(183, 207, 202));
""",
    """  // The accepted eye look now changes the visible pupil geometry rather
  // than only changing mood pose/color. This keeps the realistic koala iris
  // while making heart/star/x/round/slit/sleepy/angry immediately distinct.
  drawStyledPupil(canvas, kCenter + gazeX, eyeCy + gazeY, irisR, leftEye);
""",
    "fixed vertical pupil block",
)

path.write_text(text, encoding="utf-8")
print(f"Patched distinct DualEye look geometry: {path}")
