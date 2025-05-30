export const browserWarningMessage = (unsupportedBrowser: boolean) => (
  <>
    ⚠️ At this time, voice recording is supported exclusively on
    Chromium-based browsers (desktop and Android) such as Google Chrome, Microsoft Edge, etc.
    <br />
    ⚠️ Voice transcription is limited to English input.
    <br />
    ❗❗❗ YOU ARE {unsupportedBrowser ? "NOT on a supported browser" : "on a supported browser ✅"} ❗❗❗
    <br />
    You are currently using:
    <br />
    <code>{navigator.userAgent}</code>
  </>
);