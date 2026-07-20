# KillerKoala T114 boot splash

The firmware-ready splash is a center-cropped, aspect-preserving 240x135
version of the user-supplied bootsplash image.png. No artwork was
regenerated or stretched.

- source dimensions: 1672x941 PNG
- source SHA-256: 1584793e1fcee9fa0cf89d9912bde5eb54ad5074080c68d3934936e0a39419d5
- display preview: killerkoala-bootsplash-240x135.png
- preview SHA-256: 7e3686495125e11e9ab4814d990e96653070a5a599ae70c3ead9b33d55270504
- firmware payload: killerkoala-bootsplash-240x135.rgb565be
- payload format: row-major RGB565, most-significant byte first
- payload size: 64,800 bytes
- payload SHA-256: 7e097b1966de7bc9338a825917be4d71480bae226373eb993cf2ac8e5f0dab26

The Zephyr build converts the RGB565 payload to a generated include and
rejects a payload whose compiled size is not exactly the 240x135 framebuffer.

## Cyber-mouth expression library

Five 240x135 cartoon cyberpunk Koala mouth frames are embedded as row-major,
big-endian RGB565 payloads. Each frame carries its own ultraviolet-left and
lime-green-right rim lighting so the colored highlights and shadows move with
the muzzle, cheek, and jaw pose.

| Expression frame | RGB565 SHA-256 |
| --- | --- |
| smile | `4ac8487889927f12245b7aab18bcbae67a136d435bedfbc12d64b6438b325c0b` |
| happy/open smile | `16753b3a5ae15a9946c7a519203d181ac4c1d21a121f7de6699497bbc96c4f00` |
| bite/chew | `7473bc86850497c03067fce47f3bd2bdf6166ca0ac1cbc14f19dc579adac93cd` |
| snarl | `265f944b10b4cab58ee0d84b5e67fbec805a2cd7774829641697a3077f058ed0` |
| sideways grin | `2698c29d589abe9b3582be48f630da71ce0c3051d7656d7f4ba57556fd435e49` |

Every decoded payload is exactly 64,800 bytes. Repository copies are split
into two base64 text parts; the build decodes them and rejects any size or
SHA-256 mismatch before generating the C include. The expression state machine
maps Koalagotchi contentment/health and mood to smile, bite, snarl, and
asymmetric sideways-grin animation sequences without drawing any words on the
T114. Seven eased RGB565 interpolation steps connect idle poses, with irregular
holds so the idle loop does not look mechanical. Three-step faster transitions
move through varied open, closed, bite, and sideways poses while Pi-side or
local-AI speech is active; an explicit speech-stop event returns the mouth
smoothly to the current mood sequence.
