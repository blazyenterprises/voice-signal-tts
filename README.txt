Voice Signal TTS 0.1.0
By Blazy Enterprises

INSTALL
Open voiceSignalTTS-0.1.0.nvda-addon, install it in NVDA, then restart NVDA.
Press NVDA+Control+S and select Voice Signal TTS.
Choose a language from the Voice setting in NVDA's Speech settings or settings ring.
English (United States), Spanish (Mexico), French (Canada), Portuguese (Brazil).
Requires 64-bit Windows and NVDA 2026.1 or later. The isolated 64-bit worker can
be launched from either 32-bit or 64-bit NVDA. All runtime dependencies are bundled.
The existing Motorola V323i addon can remain installed alongside this addon.

CONTROLS
Rate 50: native speed. Rate 0: approximately half speed; 100: twice speed.
Pitch 50: unchanged. Range is approximately six semitones below/above native pitch;
pitch is processed after decoding with timing compensation, not a native control.
Volume 0..100 uses nvwave playback volume; default 100 applies no extra gain.
NVDA saves these settings through its normal synthesizer settings mechanism.
Audio uses NVDA's selected output device. Reselect the synthesizer after changing
the output device if needed. Pause, cancellation, spelling, breaks, and speech
index notifications are supported. Language commands select a matching language
or regional fallback; unsupported languages retain the selected voice.

ENGINE
Uses the original V3c firmware speech engine under bounded ARM emulation in an
isolated worker process. No phone OS or DSP emulator is needed. Speech is decoded
to 8 kHz mono PCM. Long text is split into short chunks for responsiveness;
chunk boundaries can affect pauses and intonation. Latin-1 accents are retained.
This is an independent addon, not an official Motorola, VoiceSignal or Nuance
release. Exact TTS-library version and voice actor identities remain unverified.
On synthesis failure the driver attempts to restore eSpeak and report the error.

VALIDATION
Real bundled runtime, firmware and decoder tested in all four languages,
including accented text, native rate, pitch, and numbers. Driver tests use a
recording NVDA API adapter for output device, volume, language switching,
indexes, spelling, breaks, cancellation, pause and shutdown. Actual use inside
a running NVDA installation still requires user testing.

COMPONENTS
Adapter by Blazy Enterprises. Proprietary firmware code/data comes from the
user-supplied USC_V3c_04.08.00R_PRIii05698_MONSTER_01.shx package; no ownership
or open-source licensing of that material is claimed.
Python 3.12 license: engine/runtime/LICENSE.txt.
Unicorn license: engine/vendor/unicorn-2.1.4.dist-info.
FFmpeg license: engine/FFmpeg-license.txt.
