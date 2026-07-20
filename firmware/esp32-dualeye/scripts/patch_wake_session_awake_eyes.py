Import("env")

from pathlib import Path

project = Path(env.subst("$PROJECT_DIR"))
path = project / "src" / "integrated_main_wake_session.cpp"
text = path.read_text(encoding="utf-8")

function_anchor = """void showLocalSpeakingEyes() {
  clearDisplayModes();
  clearOverlay();
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "blink", 100);
  drawKoalagotchiModeScreen("killerkoala", "calm", 85, 92);
}

"""
function_replacement = function_anchor + """void showWakeSessionEyes() {
  clearDisplayModes();
  clearOverlay();
  setKoalagotchiEyeStyle("cyber", "#A54BFF", "#32FF71", "pulse", 100);
  drawKoalagotchiModeScreen("killerkoala", "listening", 88, 96);
}

"""
if text.count(function_anchor) != 1:
    raise RuntimeError("awake-eye patch expected one showLocalSpeakingEyes anchor")
text = text.replace(function_anchor, function_replacement, 1)

return_anchor = """  showIdleEyes();
  if (resumeAfter) srResumeAt = millis() + 100;
  return played;
"""
return_replacement = """  if (wakeSessionActive) {
    showWakeSessionEyes();
  } else {
    showIdleEyes();
  }
  if (resumeAfter) srResumeAt = millis() + 100;
  return played;
"""
if text.count(return_anchor) != 1:
    raise RuntimeError("awake-eye patch expected one local-response return anchor")
text = text.replace(return_anchor, return_replacement, 1)

path.write_text(text, encoding="utf-8")
print(f"Patched visible awake-eye session state: {path}")
