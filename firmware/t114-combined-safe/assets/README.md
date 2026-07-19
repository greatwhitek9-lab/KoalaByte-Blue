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
